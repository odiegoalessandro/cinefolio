import assert from 'node:assert/strict';
import test from 'node:test';

async function loadAvatarSettingsModule() {
  try {
    return await import('../avatar-settings.js');
  } catch (error) {
    assert.fail(`avatar-settings.js must be importable without a browser: ${error.message}`);
  }
}

function control() {
  const listeners = new Map();
  return {
    disabled: false,
    files: [],
    src: '',
    textContent: '',
    value: '',
    addEventListener(eventName, listener) {
      listeners.set(eventName, listener);
    },
    async trigger(eventName) {
      if (eventName === 'click' && this.disabled) {
        return undefined;
      }
      return listeners.get(eventName)?.({ preventDefault() {} });
    },
  };
}

function createControls(initialAvatarUrl = '') {
  return {
    fileInput: control(),
    preview: control(),
    removeButton: control(),
    uploadButton: control(),
    initialAvatarUrl,
  };
}

test('selecting a local file enables upload and previews its object URL', async () => {
  const { initializeAvatarSettings } = await loadAvatarSettingsModule();
  const controls = createControls();
  const file = { name: 'avatar.png', type: 'image/png' };
  controls.fileInput.files = [file];
  const urlRef = {
    createObjectURL(receivedFile) {
      assert.equal(receivedFile, file);
      return 'blob:avatar-preview';
    },
    revokeObjectURL() {},
  };

  initializeAvatarSettings({
    apiClient: {},
    ...controls,
    urlRef,
  });
  await controls.fileInput.trigger('change');

  assert.equal(controls.preview.src, 'blob:avatar-preview');
  assert.equal(controls.uploadButton.disabled, false);
});

test('upload sends only the avatar file and renders the returned local URL', async () => {
  const { initializeAvatarSettings } = await loadAvatarSettingsModule();
  const controls = createControls();
  const file = new Blob(['image'], { type: 'image/png' });
  controls.fileInput.files = [file];
  const calls = [];
  const apiClient = {
    async putForm(path, formData) {
      calls.push({ path, formData });
      return { user: { avatar_url: '/uploads/avatars/updated.png' } };
    },
  };

  initializeAvatarSettings({
    apiClient,
    ...controls,
    urlRef: { createObjectURL: () => 'blob:selected', revokeObjectURL() {} },
  });
  await controls.fileInput.trigger('change');
  await controls.uploadButton.trigger('click');

  assert.equal(calls[0].path, '/api/profile/avatar');
  const uploadedFile = calls[0].formData.get('avatar');
  assert.equal(uploadedFile.type, 'image/png');
  assert.equal(await uploadedFile.text(), 'image');
  assert.equal(controls.preview.src, '/uploads/avatars/updated.png');
  assert.equal(controls.fileInput.value, '');
  assert.equal(controls.uploadButton.disabled, true);
});

test('removing an avatar restores the default preview after the API succeeds', async () => {
  const { initializeAvatarSettings } = await loadAvatarSettingsModule();
  const controls = createControls('/uploads/avatars/current.png');
  const messages = [];
  const apiClient = {
    async delete(path) {
      assert.equal(path, '/api/profile/avatar');
      return { user: { avatar_url: '' } };
    },
  };

  initializeAvatarSettings({
    apiClient,
    ...controls,
    onMessage: (message, isError) => messages.push({ message, isError }),
    urlRef: { createObjectURL() {}, revokeObjectURL() {} },
  });
  await controls.removeButton.trigger('click');

  assert.equal(controls.preview.src, 'assets/default-avatar.svg');
  assert.deepEqual(messages, [{ message: 'Foto de perfil removida com sucesso.', isError: false }]);
});

test('an upload blocks avatar removal until its request completes', async () => {
  const { initializeAvatarSettings } = await loadAvatarSettingsModule();
  const controls = createControls('/uploads/avatars/current.png');
  controls.fileInput.files = [new Blob(['image'], { type: 'image/png' })];
  let resolveUpload;
  let removeCalls = 0;
  const apiClient = {
    putForm() {
      return new Promise((resolve) => {
        resolveUpload = resolve;
      });
    },
    async delete() {
      removeCalls += 1;
      return { user: { avatar_url: '' } };
    },
  };

  initializeAvatarSettings({
    apiClient,
    ...controls,
    urlRef: { createObjectURL: () => 'blob:selected', revokeObjectURL() {} },
  });
  await controls.fileInput.trigger('change');
  const upload = controls.uploadButton.trigger('click');
  await controls.removeButton.trigger('click');

  assert.equal(controls.uploadButton.disabled, true);
  assert.equal(controls.removeButton.disabled, true);
  assert.equal(removeCalls, 0);

  resolveUpload({ user: { avatar_url: '/uploads/avatars/updated.png' } });
  await upload;
});
