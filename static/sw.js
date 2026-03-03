self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// (선택) fetch는 지금처럼 비워둬도 OK
self.addEventListener("fetch", () => {});

// ✅ 푸시 수신 → 알림 띄우기
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: "하테나일본어", body: event.data ? event.data.text() : "공부할 시간이에요!" };
  }

  const title = data.title || "하테나일본어";
  const options = {
    body: data.body || "오늘도 10분만 같이 가요!",
    icon: data.icon || "/static/icon-192.png",
    badge: data.badge || "/static/icon-192.png",
    data: {
      url: data.url || "/?source=push",
    },
    // 필요하면 태그/진동/액션도 추가 가능
    // tag: "hatena-study",
    // vibrate: [100, 50, 100],
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// ✅ 알림 클릭 → 앱 열기(또는 포커스)
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification && event.notification.data && event.notification.data.url) || "/";

  event.waitUntil(
    (async () => {
      const allClients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });

      for (const client of allClients) {
        // 이미 열려 있으면 그 탭으로 이동/포커스
        if ("focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }

      // 없으면 새 창 열기
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
    })()
  );
});
