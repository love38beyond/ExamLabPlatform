(function () {
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".vmspec-widget").forEach(function (widget) {
      const containerId = widget.id;
      const prefix = containerId.replace("_container", "");
      const addBtn = document.getElementById(prefix + "_add");
      const listContainer = document.getElementById(prefix + "_linux_list");
      const countInput = document.getElementById(prefix + "_linux_count");

      if (!addBtn || !listContainer || !countInput) return;

      // Remove empty placeholder
      const emptyEl = listContainer.querySelector(".vmspec-empty");

      // Re-index all linux items
      function reindex() {
        const items = listContainer.querySelectorAll(".vmspec-linux-item");
        items.forEach(function (item, idx) {
          item.dataset.index = idx;
          item.querySelectorAll("input").forEach(function (input) {
            const oldName = input.name;
            // Update index in name: _linux_role_X -> _linux_role_new
            input.name = oldName.replace(/_linux_(role|cpu|ram|disk|image_id)_\d+/, "_linux_$1_" + idx);
          });
        });
        countInput.value = items.length;
        if (items.length === 0 && emptyEl) {
          emptyEl.style.display = "block";
        } else if (emptyEl) {
          emptyEl.style.display = "none";
        }
      }

      // Add server
      addBtn.addEventListener("click", function () {
        const idx = listContainer.querySelectorAll(".vmspec-linux-item").length;
        const row = document.createElement("div");
        row.className = "vmspec-linux-item";
        row.dataset.index = idx;
        row.innerHTML =
          '<button type="button" class="vmspec-remove" title="Remove">✕</button>' +
          '<div class="vmspec-row">' +
          '  <label>Role: <input type="text" name="' + prefix + '_linux_role_' + idx + '" placeholder="e.g. Web Server" list="vmspec_roles"></label>' +
          '  <label>CPU Cores: <input type="number" name="' + prefix + '_linux_cpu_' + idx + '" value="2" min="1" max="64" class="vmspec-int"></label>' +
          '  <label>RAM (GB): <input type="number" name="' + prefix + '_linux_ram_' + idx + '" value="2" min="1" max="256" class="vmspec-int"></label>' +
          '  <label>Disk (GB): <input type="number" name="' + prefix + '_linux_disk_' + idx + '" value="40" min="20" max="500" class="vmspec-int"></label>' +
          '  <label>Image ID: <input type="text" name="' + prefix + '_linux_image_id_' + idx + '" placeholder="img-yyyyyyyy"></label>' +
          '</div>';
        listContainer.appendChild(row);
        if (emptyEl) emptyEl.style.display = "none";
        countInput.value = parseInt(countInput.value) + 1;

        // Bind remove
        row.querySelector(".vmspec-remove").addEventListener("click", function () {
          row.remove();
          reindex();
        });
      });

      // Bind existing remove buttons
      listContainer.querySelectorAll(".vmspec-remove").forEach(function (btn) {
        btn.addEventListener("click", function () {
          btn.closest(".vmspec-linux-item").remove();
          reindex();
        });
      });
    });
  });
})();
