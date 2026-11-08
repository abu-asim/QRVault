const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");
const uploadCard = document.getElementById("uploadCard");
const selectedFiles = document.getElementById("selectedFiles");

const uploadSubmitBtn = document.getElementById("uploadSubmitBtn");
const uploadStatus = document.getElementById("uploadStatus");

const qrResults = document.getElementById("qrResults");
const qrGrid = document.getElementById("qrGrid");

const expirySelect = document.getElementById("expirySelect");

const MAX_FILE_SIZE = 100 * 1024 * 1024;

let files = [];


// Open File Picker

uploadBtn.addEventListener("click", () => {
    fileInput.click();
});


// File Selection

fileInput.addEventListener("change", () => {

    addFiles(fileInput.files);

    fileInput.value = "";

});


// Add Files

function addFiles(newFiles) {

    Array.from(newFiles).forEach(file => {

        if (file.size > MAX_FILE_SIZE) {

            alert(`${file.name} exceeds 100 MB.`);

            return;
        }

        const duplicate = files.some(existing =>
            existing.name === file.name &&
            existing.size === file.size &&
            existing.lastModified === file.lastModified
        );

        if (!duplicate) {
            files.push(file);
        }

    });

    renderFiles();

}


// Render Selected Files

function renderFiles() {

    selectedFiles.innerHTML = "";

    if (files.length === 0) {

        selectedFiles.style.display = "none";
        uploadSubmitBtn.style.display = "none";

        return;
    }

    selectedFiles.style.display = "block";
    uploadSubmitBtn.style.display = "inline-block";

    files.forEach((file, index) => {

        const item = document.createElement("div");

        item.className = "file-item";

        const name = document.createElement("span");

        name.className = "file-name";
        name.textContent = file.name;

        const size = document.createElement("span");

        size.className = "file-size";
        size.textContent = formatSize(file.size);

        const remove = document.createElement("button");

        remove.className = "remove-file";
        remove.textContent = "×";

        remove.addEventListener("click", () => {

            files.splice(index, 1);

            renderFiles();

        });

        item.append(name, size, remove);

        selectedFiles.appendChild(item);

    });

}


// Format File Size

function formatSize(bytes) {

    if (bytes < 1024 * 1024) {

        return (bytes / 1024).toFixed(1) + " KB";

    }

    return (bytes / (1024 * 1024)).toFixed(2) + " MB";

}


// Drag & Drop

uploadCard.addEventListener("dragover", event => {

    event.preventDefault();

    uploadCard.classList.add("drag-active");

});


uploadCard.addEventListener("dragleave", event => {

    if (!uploadCard.contains(event.relatedTarget)) {

        uploadCard.classList.remove("drag-active");

    }

});


uploadCard.addEventListener("drop", event => {

    event.preventDefault();

    uploadCard.classList.remove("drag-active");

    addFiles(event.dataTransfer.files);

});


// Upload Files

uploadSubmitBtn.addEventListener("click", () => {

    if (files.length === 0) return;

    const formData = new FormData();

    // Append selected files

    files.forEach(file => {

        formData.append("files", file);

    });


    // Append selected expiry option

    formData.append("expiry", expirySelect.value);


    const csrfToken = document.querySelector(
        '[name=csrfmiddlewaretoken]'
    ).value;

    const xhr = new XMLHttpRequest();

    xhr.open("POST", "/api/upload/");

    xhr.setRequestHeader("X-CSRFToken", csrfToken);

    uploadSubmitBtn.disabled = true;

    uploadBtn.disabled = true;

    expirySelect.disabled = true;

    uploadStatus.textContent = "Preparing upload...";


    xhr.upload.addEventListener("progress", event => {

        if (event.lengthComputable) {

            const percentage = Math.round(
                (event.loaded / event.total) * 100
            );

            uploadStatus.textContent =
                `Uploading... ${percentage}%`;

        }

    });


    xhr.onload = () => {

        let response;

        try {

            response = JSON.parse(xhr.responseText);

        } catch {

            uploadStatus.textContent = "Invalid server response.";

            uploadSubmitBtn.disabled = false;
            uploadBtn.disabled = false;
            expirySelect.disabled = false;

            return;
        }


        if (xhr.status === 200 && response.success) {

            uploadStatus.textContent =
                "✓ " + response.message;

            displayQRCodes(response.files);

            files = [];

            renderFiles();

        } else {

            uploadStatus.textContent =
                "✕ " + (response.message || "Upload failed.");

        }

        uploadSubmitBtn.disabled = false;
        uploadBtn.disabled = false;
        expirySelect.disabled = false;

    };


    xhr.onerror = () => {

        uploadStatus.textContent = "Network error!";

        uploadSubmitBtn.disabled = false;
        uploadBtn.disabled = false;
        expirySelect.disabled = false;

    };


    xhr.send(formData);

});


// Display Generated QR Codes

function displayQRCodes(uploadedFiles) {

    qrGrid.innerHTML = "";

    qrResults.style.display = "block";

    uploadedFiles.forEach(file => {

        const card = document.createElement("div");

        card.className = "qr-card";


        const title = document.createElement("h3");

        title.textContent = file.name;


        const image = document.createElement("img");

        image.src = file.qr_url;
        image.alt = "QR Code for " + file.name;


        const size = document.createElement("p");

        size.textContent = "Size: " + formatSize(file.size);


        const download = document.createElement("a");

        download.href = file.qr_url;

        download.download = `QRVault-${file.id}.png`;

        download.textContent = "Download QR";


        const copy = document.createElement("button");

        copy.className = "copy-btn";

        copy.textContent = "Copy Share Link";


        copy.addEventListener("click", async () => {

            try {

                await navigator.clipboard.writeText(file.share_url);

                copy.textContent = "Copied! ✓";

                setTimeout(() => {
                    copy.textContent = "Copy Share Link";
                }, 2000);

            } catch {

                window.prompt(
                    "Copy your sharing link:",
                    file.share_url
                );

            }

        });


        card.append(
            title,
            image,
            size,
            download,
            copy
        );

        qrGrid.appendChild(card);

    });

    qrResults.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });

}