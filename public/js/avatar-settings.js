import { avatarImageUrl } from './images.js';

// Callback "vazio" usado como padrão quando quem chama esta função não
// quer receber mensagens de feedback (evita checar "if (onMessage)" toda hora)
const DEFAULT_MESSAGE = () => {};


// Este módulo encapsula toda a lógica de trocar/remover o avatar: recebe
// os elementos do DOM já prontos (em vez de buscá-los sozinho), o que o
// torna reutilizável e fácil de testar isoladamente
export function initializeAvatarSettings({
  apiClient,
  fileInput,  // <input type="file"> onde o usuário escolhe a imagem
  preview,   // <img> que mostra a prévia do avatar
  removeButton,
  uploadButton,
  initialAvatarUrl = '',
  onMessage = DEFAULT_MESSAGE,
  urlRef = URL, // permite injetar um "URL" falso em testes (createObjectURL/revokeObjectURL)
}) {
  let currentAvatarUrl = initialAvatarUrl;  // avatar já salvo no servidor
  let isOperationInProgress = false;  // trava contra ações simultâneas (duplo clique)
  let previewObjectUrl = null;      // URL temporária de pré-visualização local
  let selectedFile = null;  // arquivo escolhido mas ainda não enviado

  function updateActionAvailability() {
    // O botão de "Enviar" só fica ativo se: não há operação em andamento
    // E existe um arquivo selecionado para enviar
    uploadButton.disabled = isOperationInProgress || !selectedFile;
    removeButton.disabled = isOperationInProgress;
  }

  function revokePreviewObjectUrl() {
    // URL.createObjectURL cria uma URL temporária que aponta para um
    // arquivo local (sem precisar fazer upload primeiro, só para
    // pré-visualização); ela PRECISA ser "revogada" manualmente depois de
    // usada, senão o navegador mantém o arquivo em memória
    // desnecessariamente (vazamento de memória)
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
    // Roda quando o usuário escolhe (ou desmarca) um arquivo no <input type="file">
    selectedFile = fileInput.files?.[0] || null;
    updateActionAvailability();

    if (!selectedFile) {
      // Nenhum arquivo selecionado: volta a mostrar o avatar atual salvo
      setAvatarUrl(currentAvatarUrl);
      return;
    }

    // Mostra uma prévia INSTANTÂNEA do arquivo escolhido, antes mesmo de
    // enviá-lo ao servidor (createObjectURL gera uma URL local temporária
    // que aponta direto para o arquivo no disco do usuário)
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
      // Alguns arquivos (ex: vindos de uma câmera/webcam via canvas) podem
      // não ter um "name" — o FormData.set aceita o terceiro argumento
      // (nome do arquivo) só quando ele existe
      if (selectedFile.name) {
        formData.set('avatar', selectedFile, selectedFile.name);
      } else {
        formData.set('avatar', selectedFile);
      }

      const { user } = await apiClient.putForm('/api/profile/avatar', formData);
      selectedFile = null;
      fileInput.value = '';   // limpa o campo de arquivo (senão o mesmo arquivo "preso" no input não dispararia o evento "change" se selecionado de novo)
      setAvatarUrl(user.avatar_url);  // atualiza a prévia com a URL REAL retornada pelo servidor
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
      setAvatarUrl(user.avatar_url);  // volta para o avatar padrão (vazio)
      onMessage('Foto de perfil removida com sucesso.', false);
    } catch (error) {
      onMessage(error.message, true);
    } finally {
      isOperationInProgress = false;
      updateActionAvailability();
    }
  }

  // Configuração inicial: mostra o avatar atual, define o estado inicial
  // dos botões e conecta os eventos aos elementos recebidos
  setAvatarUrl(currentAvatarUrl);
  updateActionAvailability();
  fileInput.addEventListener('change', updateSelectedFile);
  uploadButton.addEventListener('click', uploadAvatar);
  removeButton.addEventListener('click', removeAvatar);

  // Expõe setAvatarUrl para quem criou este módulo poder, por exemplo,
  // sincronizar a prévia se o avatar for alterado por outra parte da página
  return Object.freeze({ setAvatarUrl });
}
