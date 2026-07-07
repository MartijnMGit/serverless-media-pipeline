const fileInput = document.getElementById("file-input");
const uploadButton = document.getElementById("upload-button");
const uploadStatus = document.getElementById("upload-status");
const refreshButton = document.getElementById("refresh-button");
const gallery = document.getElementById("gallery");

const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ATTEMPTS = 20;

uploadButton.addEventListener("click", handleUpload);
refreshButton.addEventListener("click", loadGallery);

async function handleUpload() {
  const file = fileInput.files[0];
  if (!file) {
    setStatus("Choose a file first.");
    return;
  }

  uploadButton.disabled = true;
  try {
    setStatus("Requesting upload URL...");
    const presignResponse = await fetch("/api/uploads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: file.name, content_type: file.type }),
    });
    if (!presignResponse.ok) {
      throw new Error((await presignResponse.json()).error || "Failed to get upload URL");
    }
    const { image_id, upload_url } = await presignResponse.json();

    setStatus("Uploading...");
    const putResponse = await fetch(upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.type },
      body: file,
    });
    if (!putResponse.ok) {
      throw new Error("Upload to S3 failed");
    }

    setStatus("Uploaded. Processing (thumbnail + Rekognition labels)...");
    await pollForResult(image_id);
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  } finally {
    uploadButton.disabled = false;
  }
}

async function pollForResult(imageId) {
  for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt++) {
    await sleep(POLL_INTERVAL_MS);
    const response = await fetch(`/api/images/${imageId}`);
    if (response.status === 404) {
      continue;
    }
    const item = await response.json();
    if (item.status === "COMPLETE") {
      setStatus("Done! See it below.");
      await loadGallery();
      return;
    }
  }
  setStatus("Still processing - refresh in a bit.");
}

async function loadGallery() {
  try {
    const response = await fetch("/api/images");
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    const { images } = await response.json();
    gallery.innerHTML = images.length
      ? images.map(renderCard).join("")
      : "<p class=\"labels\">No uploads yet - be the first!</p>";
  } catch (err) {
    gallery.innerHTML = `<p class="labels">Could not load gallery (${escapeHtml(err.message)}).</p>`;
  }
}

function renderCard(item) {
  const labels = (item.labels || []).map((l) => l.name).join(", ") || "No labels yet";
  const thumb = item.thumbnail_url || "";
  return `
    <div class="card">
      <img src="${thumb}" alt="${escapeHtml(item.image_id)}" loading="lazy">
      <div class="card-body">
        <p class="status">${escapeHtml(item.status || "processing")}</p>
        <p class="labels">${escapeHtml(labels)}</p>
      </div>
    </div>
  `;
}

function setStatus(message) {
  uploadStatus.textContent = message;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

loadGallery();
