(() => {
  const list = document.getElementById('chatMessageList');
  if (!list || !list.dataset.pollUrl) return;
  let lastId = Number(list.dataset.lastId || 0);
  let polling = false;

  const safeText = (value) => String(value ?? '');

  function appendMessage(item) {
    if (list.querySelector(`[data-message-id="${Number(item.id)}"]`)) return;
    const row = document.createElement('article');
    row.className = `chat-message${item.is_mine ? ' message-mine' : ''}`;
    row.dataset.messageId = String(item.id);

    let avatar;
    if (item.avatar_url) {
      avatar = document.createElement('img');
      avatar.className = 'avatar avatar-tiny avatar-photo';
      avatar.src = item.avatar_url;
      avatar.alt = `Photo de ${safeText(item.sender || item.username || 'membre')}`;
      avatar.loading = 'lazy';
    } else {
      avatar = document.createElement('span');
      avatar.className = 'avatar avatar-tiny';
      avatar.textContent = (item.username || '?').slice(0, 1).toUpperCase();
      avatar.setAttribute('aria-hidden', 'true');
    }

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    const sender = document.createElement('div');
    sender.className = 'chat-sender';
    sender.textContent = safeText(item.sender);
    const time = document.createElement('time');
    time.textContent = safeText(item.created_at);
    sender.appendChild(document.createTextNode(' '));
    sender.appendChild(time);

    const text = document.createElement('p');
    text.textContent = safeText(item.content);
    bubble.appendChild(sender);
    bubble.appendChild(text);
    row.appendChild(avatar);
    row.appendChild(bubble);
    const empty = document.getElementById('chatEmpty');
    if (empty) empty.remove();
    list.appendChild(row);
    lastId = Math.max(lastId, Number(item.id));
  }

  async function poll() {
    if (polling || document.hidden) return;
    polling = true;
    try {
      const url = new URL(list.dataset.pollUrl, window.location.origin);
      url.searchParams.set('after', String(lastId));
      const response = await fetch(url.toString(), {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
      });
      if (response.status === 401 || response.status === 403) return;
      if (!response.ok) return;
      const result = await response.json();
      (result.messages || []).forEach(appendMessage);
      list.dataset.lastId = String(lastId);
      if ((result.messages || []).length) list.scrollTop = list.scrollHeight;
    } catch (_) {
      // Ignore temporary connectivity errors; polling will retry at next interval.
    } finally {
      polling = false;
    }
  }

  list.scrollTop = list.scrollHeight;
  window.setInterval(poll, 5000);
})();
