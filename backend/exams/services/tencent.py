"""Tencent Cloud CVM service wrapper."""
import logging
import secrets
import string

from django.conf import settings
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)
from tencentcloud.cvm.v20170312 import cvm_client, models as cvm_models
from tencentcloud.vpc.v20170312 import vpc_client, models as vpc_models

logger = logging.getLogger(__name__)


def _get_cvm_client():
    cred = credential.Credential(
        settings.TENCENT_SECRET_ID, settings.TENCENT_SECRET_KEY
    )
    return cvm_client.CvmClient(cred, settings.TENCENT_REGION)


def _get_vpc_client():
    cred = credential.Credential(
        settings.TENCENT_SECRET_ID, settings.TENCENT_SECRET_KEY
    )
    return vpc_client.VpcClient(cred, settings.TENCENT_REGION)


def create_security_group(name: str) -> str:
    """Create a security group for one student. Returns security group ID."""
    client = _get_vpc_client()
    req = vpc_models.CreateSecurityGroupRequest()
    req.GroupName = name
    req.GroupDescription = f"Exam security group - {name}"
    resp = client.CreateSecurityGroup(req)
    sg_id = resp.SecurityGroup.SecurityGroupId

    # Allow all traffic within the same security group
    def _make_policy(sg_id):
        p = vpc_models.SecurityGroupPolicy()
        p.Protocol = "ALL"
        p.Port = "ALL"
        p.SecurityGroupId = sg_id
        p.Action = "ACCEPT"
        return p

    # Add ingress rule
    in_policy_set = vpc_models.SecurityGroupPolicySet()
    in_policy_set.Ingress = [_make_policy(sg_id)]
    in_req = vpc_models.CreateSecurityGroupPoliciesRequest()
    in_req.SecurityGroupId = sg_id
    in_req.SecurityGroupPolicySet = in_policy_set
    client.CreateSecurityGroupPolicies(in_req)

    # Add egress rule (separate call required by API)
    out_policy_set = vpc_models.SecurityGroupPolicySet()
    out_policy_set.Egress = [_make_policy(sg_id)]
    out_req = vpc_models.CreateSecurityGroupPoliciesRequest()
    out_req.SecurityGroupId = sg_id
    out_req.SecurityGroupPolicySet = out_policy_set
    client.CreateSecurityGroupPolicies(out_req)

    logger.info("Created security group %s: %s", name, sg_id)
    return sg_id


def run_instances(
    image_id, instance_type, instance_count, vpc_id, subnet_id,
    security_group_ids, instance_name_prefix, password="", disk_size=50,
    user_data="",
):
    """Create CVM instances. Optionally pass user_data for cloud-init.

    user_data should be a base64-encoded shell script (Linux) or
    PowerShell script (Windows). Max 16KB.
    """
    client = _get_cvm_client()
    req = cvm_models.RunInstancesRequest()
    req.ImageId = image_id
    req.InstanceType = instance_type
    req.InstanceCount = instance_count
    req.InstanceChargeType = "POSTPAID_BY_HOUR"
    placement = cvm_models.Placement()
    placement.Zone = settings.TENCENT_ZONE
    req.Placement = placement
    vpc = cvm_models.VirtualPrivateCloud()
    vpc.VpcId = vpc_id
    vpc.SubnetId = subnet_id
    req.VirtualPrivateCloud = vpc
    req.SecurityGroupIds = security_group_ids
    req.InstanceName = instance_name_prefix
    sys_disk = cvm_models.SystemDisk()
    sys_disk.DiskType = "CLOUD_PREMIUM"
    sys_disk.DiskSize = disk_size
    req.SystemDisk = sys_disk
    if password:
        login = cvm_models.LoginSettings()
        login.Password = password
        req.LoginSettings = login
    if user_data:
        import base64
        req.UserData = base64.b64encode(user_data.encode()).decode()

    try:
        resp = client.RunInstances(req)
        instance_ids = resp.InstanceIdSet
        logger.info("Launched instances: %s", instance_ids)
        return instance_ids
    except TencentCloudSDKException as e:
        logger.error("Failed to create instances: %s", e)
        raise


def describe_instances(instance_ids):
    """Get instance details including private IP."""
    client = _get_cvm_client()
    req = cvm_models.DescribeInstancesRequest()
    req.InstanceIds = instance_ids
    resp = client.DescribeInstances(req)
    results = []
    for item in resp.InstanceSet:
        results.append({
            "instance_id": item.InstanceId,
            "private_ip": (
                item.PrivateIpAddresses[0]
                if item.PrivateIpAddresses else ""
            ),
            "state": item.InstanceState,
        })
    return results


def terminate_instances(instance_ids):
    """Destroy CVM instances."""
    client = _get_cvm_client()
    req = cvm_models.TerminateInstancesRequest()
    req.InstanceIds = instance_ids
    client.TerminateInstances(req)


def get_instance_type(cpu, ram):
    """Map CPU/RAM to Tencent Cloud instance type."""
    mapping = {
        (1, 1): "S5.SMALL1",
        (1, 2): "S5.SMALL2",
        (2, 2): "S5.MEDIUM4",
        (2, 4): "S5.MEDIUM2",
        (4, 8): "S5.LARGE4",
        (4, 16): "S5.LARGE8",
    }
    return mapping.get((cpu, ram), "S5.MEDIUM2")


def generate_password(length=12):
    """Generate a random Windows admin password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_vms_for_exam(exam) -> dict:
    """Create all VMs for an exam. Returns {success: N, error: N}."""
    from ..models import VmGroup, VmInstance

    vm_spec = exam.vm_spec
    windows_spec = vm_spec.get("windows")  # None if unchecked
    linux_servers = vm_spec.get("linux_servers", [])

    groups = VmGroup.objects.filter(exam=exam).select_related("student")
    success_count = 0
    error_count = 0

    for group in groups:
        try:
            # Create security group for this student
            sg_name = f"exam-{exam.id}-student-{group.student_id}"
            sg_id = create_security_group(sg_name)
            group.security_group_id = sg_id
            group.save(update_fields=["security_group_id"])

            # Create Windows VM (optional)
            if windows_spec:
                win_type = get_instance_type(windows_spec["cpu"], windows_spec["ram"])
                password = generate_password()
                win_ids = run_instances(
                    image_id=windows_spec.get("image_id", ""),
                    instance_type=win_type,
                    instance_count=1,
                    vpc_id=settings.TENCENT_VPC_ID,
                    subnet_id=settings.TENCENT_SUBNET_ID_PRIVATE,
                    security_group_ids=[sg_id],
                    instance_name_prefix=f"exam-{exam.id}-win-{group.student.username}",
                    password=password,
                    disk_size=windows_spec.get("disk", 50),
                )

                if win_ids:
                    VmInstance.objects.create(
                        group=group,
                        vm_type=VmInstance.VmType.WINDOWS,
                        role_label="Windows",
                        cpu=windows_spec["cpu"],
                        ram=windows_spec["ram"],
                        disk=windows_spec["disk"],
                        image_id=windows_spec.get("image_id", ""),
                        cvm_instance_id=win_ids[0],
                        admin_password=password,
                        status=VmInstance.Status.CREATING,
                    )

            # Create Linux VMs
            linux_username = f"exam"
            linux_password = generate_password()

            for i, linux_spec in enumerate(linux_servers):
                linux_type = get_instance_type(
                    linux_spec["cpu"], linux_spec["ram"]
                )
                # Build cloud-init script: create student account on first boot
                linux_userdata = (
                    f"#!/bin/bash\n"
                    f"useradd -m {linux_username} 2>/dev/null || true\n"
                    f"echo '{linux_username}:{linux_password}' | chpasswd\n"
                    f"echo '{linux_username} ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/{linux_username}\n"
                )
                linux_ids = run_instances(
                    image_id=linux_spec.get("image_id", ""),
                    instance_type=linux_type,
                    instance_count=1,
                    vpc_id=settings.TENCENT_VPC_ID,
                    subnet_id=settings.TENCENT_SUBNET_ID_PRIVATE,
                    security_group_ids=[sg_id],
                    instance_name_prefix=(
                        f"exam-{exam.id}-linux{i+1}-{group.student.username}"
                    ),
                    disk_size=linux_spec.get("disk", 40),
                    user_data=linux_userdata,
                )

                if linux_ids:
                    VmInstance.objects.create(
                        group=group,
                        vm_type=VmInstance.VmType.LINUX,
                        role_label=linux_spec.get("role", f"Linux-{i+1}"),
                        cpu=linux_spec["cpu"],
                        ram=linux_spec["ram"],
                        disk=linux_spec["disk"],
                        image_id=linux_spec.get("image_id", ""),
                        cvm_instance_id=linux_ids[0],
                        admin_username=linux_username,
                        admin_password=linux_password,
                        status=VmInstance.Status.CREATING,
                    )

            success_count += 1
        except Exception:
            logger.exception("Failed to create VMs for group %s", group.id)
            error_count += 1

    if success_count > 0:
        exam.status = exam.Status.RUNNING
        exam.save(update_fields=["status"])

    return {"success": success_count, "error": error_count}
