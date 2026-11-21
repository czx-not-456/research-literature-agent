const createTopicLink = document.querySelector("[data-open-topic]");
if (createTopicLink) {
  createTopicLink.addEventListener("click", (event) => {
    event.preventDefault();
    const form = document.querySelector(".new-topic");
    form.open = true;
    form.querySelector('[name="name"]').focus();
  });
}

for (const form of document.querySelectorAll("[data-upload]")) {
  form.addEventListener("submit", () => {
    const button = form.querySelector('button[type="submit"]');
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
