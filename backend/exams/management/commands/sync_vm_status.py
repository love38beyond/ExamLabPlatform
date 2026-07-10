"""Django management command to sync VM IPs and status from Tencent Cloud."""
from django.core.management.base import BaseCommand
from exams.models import VmInstance
from exams.services.tencent import describe_instances


class Command(BaseCommand):
    help = "Sync VM private IPs and status from Tencent Cloud"

    def handle(self, *args, **options):
        instances = VmInstance.objects.exclude(
            cvm_instance_id=""
        ).exclude(status=VmInstance.Status.TERMINATED)

        # Batch in groups of 100 (API limit)
        all_ids = list(instances.values_list("cvm_instance_id", flat=True))
        for i in range(0, len(all_ids), 100):
            batch = all_ids[i : i + 100]
            try:
                results = describe_instances(batch)
                result_map = {r["instance_id"]: r for r in results}
                for inst in instances.filter(cvm_instance_id__in=batch):
                    info = result_map.get(inst.cvm_instance_id)
                    if info:
                        inst.private_ip = info["private_ip"]
                        if info["state"] == "RUNNING":
                            inst.status = VmInstance.Status.RUNNING
                        elif info["state"] == "STOPPED":
                            inst.status = VmInstance.Status.STOPPED
                        inst.save(update_fields=["private_ip", "status"])
                self.stdout.write(
                    self.style.SUCCESS(f"Synced {len(batch)} instances")
                )
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Error syncing batch: {e}")
                )
