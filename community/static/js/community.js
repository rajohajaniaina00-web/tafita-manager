(() => {
  const toggle = document.getElementById('communityMenuToggle');
  const sidebar = document.getElementById('communitySidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', () => {
      const open = sidebar.classList.toggle('sidebar-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('click', (event) => {
      if (window.innerWidth <= 900 && sidebar.classList.contains('sidebar-open') &&
          !sidebar.contains(event.target) && !toggle.contains(event.target)) {
        sidebar.classList.remove('sidebar-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  const copyButton = document.getElementById('copyInvitationCode');
  const code = document.getElementById('generatedCode');
  if (copyButton && code) {
    copyButton.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(code.textContent.trim());
        copyButton.textContent = 'Code copié ✓';
      } catch (_) {
        const range = document.createRange();
        range.selectNodeContents(code);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        copyButton.textContent = 'Sélectionnez et copiez le code';
      }
    });
  }

  document.querySelectorAll('input[type="file"]').forEach((input) => {
    input.addEventListener('change', () => {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (label && input.files && input.files[0]) label.textContent = `Image : ${input.files[0].name}`;
    });
  });
})();
