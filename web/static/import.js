(function () {
  const form = document.getElementById("import-upload-form");
  const dropzone = document.getElementById("import-dropzone");
  const fileInput = document.getElementById("import-files");
  const folderInput = document.getElementById("import-folder");
  const pickFilesBtn = document.getElementById("pick-files");
  const pickFolderBtn = document.getElementById("pick-folder");
  const statusEl = document.getElementById("import-status");

  if (!form || !dropzone || !fileInput) {
    return;
  }

  const ACCEPTED = [".jpg", ".jpeg", ".png", ".heic", ".heif", ".zip"];

  function isAccepted(file) {
    const name = file.name.toLowerCase();
    return ACCEPTED.some((ext) => name.endsWith(ext));
  }

  function setStatus(message) {
    if (statusEl) {
      statusEl.textContent = message || "";
    }
  }

  function assignFiles(files) {
    const accepted = Array.from(files).filter(isAccepted);
    if (!accepted.length) {
      setStatus("No supported images or ZIP files found.");
      return false;
    }
    const dt = new DataTransfer();
    accepted.forEach((file) => dt.items.add(file));
    fileInput.files = dt.files;
    setStatus(
      accepted.length === 1
        ? "1 file ready to upload."
        : `${accepted.length} files ready to upload.`
    );
    return true;
  }

  function submitWithFiles(files) {
    if (assignFiles(files)) {
      form.requestSubmit();
    }
  }

  pickFilesBtn?.addEventListener("click", () => fileInput.click());
  pickFolderBtn?.addEventListener("click", () => folderInput?.click());

  fileInput.addEventListener("change", () => {
    if (fileInput.files?.length) {
      assignFiles(fileInput.files);
    }
  });

  folderInput?.addEventListener("change", () => {
    if (folderInput.files?.length) {
      submitWithFiles(folderInput.files);
    }
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    const files = event.dataTransfer?.files;
    if (files?.length) {
      submitWithFiles(files);
    }
  });

  dropzone.addEventListener("click", (event) => {
    if (event.target === fileInput || event.target === folderInput) {
      return;
    }
    fileInput.click();
  });

  form.addEventListener("submit", () => {
    setStatus("Uploading…");
  });
})();
