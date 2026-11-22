const createTopicLink = document.querySelector("[data-open-topic]");
if (createTopicLink) {
  createTopicLink.addEventListener("click", (event) => {
    event.preventDefault();
    const form = document.querySelector(".new-topic");
    form.open = true;
    form.querySelector('[name="name"]').focus();
  });
}

const renameTopic = document.querySelector("[data-rename-topic]");
if (renameTopic) {
  renameTopic.addEventListener("toggle", () => {
    if (renameTopic.open) renameTopic.querySelector("#topic-name").focus();
  });
}

for (const form of document.querySelectorAll("[data-upload]")) {
  const input = form.querySelector('input[type="file"]');
  const button = form.querySelector('button[type="submit"]');

  if (typeof DataTransfer === "function") {
    const queue = form.querySelector("[data-upload-queue]");
    const status = form.querySelector("[data-upload-status]");
    const list = form.querySelector("[data-upload-list]");
    const maxFiles = Number(form.dataset.maxFiles);
    const maxMib = Number(form.dataset.maxMib);
    const maxBatchMib = Number(form.dataset.maxBatchMib);
    const mib = 1024 * 1024;
    let selected = [];

    function updateQueue(message = "") {
      const transfer = new DataTransfer();
      for (const file of selected) transfer.items.add(file);
      input.files = transfer.files;
      list.replaceChildren();
      for (const [index, file] of selected.entries()) {
        const item = document.createElement("li");
        const name = document.createElement("span");
        name.textContent = file.name;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "button";
        remove.textContent = "移除";
        remove.setAttribute("aria-label", '移除 ' + file.name);
        remove.addEventListener("click", () => {
          selected.splice(index, 1);
          updateQueue();
          (list.children[index]?.querySelector("button") || input).focus();
        });
        item.append(name, remove);
        list.append(item);
      }
      const count = selected.length;
      status.textContent = message || (count ? '已选 ' + count + ' 份。可以继续选择文件。' : "");
      queue.hidden = !count && !message;
    }

    input.addEventListener("change", () => {
      const added = Array.from(input.files);
      const next = [...selected, ...added];
      if (next.length > maxFiles) {
        updateQueue('每批最多选择 ' + maxFiles + ' 份 PDF，已保留原选择。');
      } else if (added.some(file => file.size > maxMib * mib)) {
        updateQueue('单份 PDF 不能超过 ' + maxMib + ' MiB，已保留原选择。');
      } else if (next.reduce((sum, file) => sum + file.size, 0) > maxBatchMib * mib) {
        updateQueue('本批文件合计不能超过 ' + maxBatchMib + ' MiB，已保留原选择。');
      } else {
        selected = next;
        updateQueue();
      }
    });
  }

  form.addEventListener("submit", () => {
    button.disabled = true;
    button.textContent = "正在解析 PDF…";
  });
}

for (const preview of document.querySelectorAll("[data-pdf-preview]")) {
  const showFailure = () => {
    preview.hidden = true;
    preview.parentElement.querySelector("[data-preview-error]").hidden = false;
  };
  preview.addEventListener("error", showFailure);
  if (preview.complete && preview.naturalWidth === 0) showFailure();
}
