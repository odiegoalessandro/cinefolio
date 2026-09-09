import { avatarImageUrl } from './images.js';

const DEFAULT_MESSAGE = () => {};

export function initializeAvatarSettings({
  apiClient,
  fileInput,
  preview,
  removeButton,
  uploadButton,
  initialAvatarUrl = '',
  onMessage = DEFAULT_MESSAGE,
  urlRef = URL,
}) {
  let currentAvatarUrl = initialAvatarUrl;
  let isOperationInProgress = false;
  let previewObjectUrl = null;
  let selectedFile = null;

  function updateActionAvailability() {
    uploadButton.disabled = isOperationInProgress || !selectedFile;
    removeButton.disabled = isOperationInProgress;
  }

  function revokePreviewObjectUrl() {
    if (previewObjectUrl) {
      urlRef.revokeObjectURL(previewObjectUrl);
      previewObjectUrl = null;
    }
  }

  function setAvatarUrl(avatarUrl) {
    revokePreviewObjectUrl();
    currentAvatarUrl = avatarUrl || '';
    preview.src = avatarImageUrl(currentAvatarUrl);
  }

  function updateSelectedFile() {
    selectedFile = fileInput.files?.[0] || null;
    updateActionAvailability();

    if (!selectedFile) {
      setAvatarUrl(currentAvatarUrl);
      return;
    }

    revokePreviewObjectUrl();
    previewObjectUrl = urlRef.createObjectURL(selectedFile);
    preview.src = previewObjectUrl;
  }

  async function uploadAvatar() {
    if (!selectedFile || isOperationInProgress) {
      return;
    }

    isOperationInProgress = true;
    updateActionAvailability();
    try {
      const formData = new FormData();
      if (selectedFile.name) {
        formData.set('avatar', selectedFile, selectedFile.name);
      } else {
        formData.set('avatar', selectedFile);
      }

      const { user } = await apiClient.putForm('/api/profile/avatar', formData);
      selectedFile = null;
      fileInput.value = '';
      setAvatarUrl(user.avatar_url);
      onMessage('Foto de perfil atualizada com sucesso.', false);
    } catch (error) {
      onMessage(error.message, true);
    } finally {
      isOperationInProgress = false;
      updateActionAvailability();
    }
  }

  async function removeAvatar() {
    if (isOperationInProgress) {
      return;
    }

    isOperationInProgress = true;
    updateActionAvailability();
    try {
      const { user } = await apiClient.delete('/api/profile/avatar');
      selectedFile = null;
      fileInput.value = '';
      uploadButton.disabled = true;
      setAvatarUrl(user.avatar_url);
      onMessage('Foto de perfil removida com sucesso.', false);
    } catch (error) {
      onMessage(error.message, true);
    } finally {
      isOperationInProgress = false;
      updateActionAvailability();
    }
  }

  setAvatarUrl(currentAvatarUrl);
  updateActionAvailability();
  fileInput.addEventListener('change', updateSelectedFile);
  uploadButton.addEventListener('click', uploadAvatar);
  removeButton.addEventListener('click', removeAvatar);

  return Object.freeze({ setAvatarUrl });
}
