/* LOGOS — interactions légères (sans dépendance externe) */
(function () {
  "use strict";
  var root = document.documentElement;

  /* Thème clair / sombre ---------------------------------------------------- */
  var themeBtn = document.querySelector("[data-theme-toggle]");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var current = root.getAttribute("data-theme");
      if (!current) current = "light";
      var next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("logos-theme", next); } catch (e) {}
    });
  }

  /* Menu mobile -------------------------------------------------------------- */
  var menuBtn = document.querySelector("[data-menu-toggle]");
  var nav = document.getElementById("main-nav");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  /* Copier le lien ------------------------------------------------------------ */
  document.querySelectorAll("[data-copy-link]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var url = btn.getAttribute("data-copy-link");
      var ok = document.querySelector(".copy-ok");
      var done = function () { if (ok) { ok.classList.add("show"); setTimeout(function () { ok.classList.remove("show"); }, 2000); } };
      if (navigator.share && /Mobi|Android/i.test(navigator.userAgent)) {
        navigator.share({ title: document.title, url: url }).catch(function () {});
        return;
      }
      if (navigator.clipboard) { navigator.clipboard.writeText(url).then(done, function () {}); }
    });
  });

  var article = document.querySelector("[data-article]");
  if (!article) return;
  var prose = article.querySelector(".prose");

  /* Table des matières -------------------------------------------------------- */
  var slugify = function (t) {
    return t.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
  };
  var headings = prose ? Array.prototype.slice.call(prose.querySelectorAll("h2, h3")) : [];
  headings = headings.filter(function (h) { return !h.closest(".keypoints, .timeline, .callout") && h.textContent.trim(); });
  var tocList = document.querySelector("[data-toc]");
  var tocMobile = document.querySelector("[data-toc-mobile]");
  if (headings.length >= 3 && tocList) {
    var used = {};
    headings.forEach(function (h) {
      if (!h.id) {
        var id = slugify(h.textContent) || "section";
        while (used[id]) { id += "-2"; }
        used[id] = true;
        h.id = id;
      }
      var mk = function () {
        var li = document.createElement("li");
        li.className = "lvl-" + h.tagName.substring(1);
        var a = document.createElement("a");
        a.href = "#" + h.id;
        a.textContent = h.textContent.trim();
        li.appendChild(a);
        return li;
      };
      tocList.appendChild(mk());
      if (tocMobile && h.tagName === "H2") tocMobile.appendChild(mk());
    });
    document.querySelectorAll(".toc, .toc-mobile").forEach(function (el) { el.hidden = false; });

    if ("IntersectionObserver" in window) {
      var links = tocList.querySelectorAll("a");
      var setActive = function (id) {
        links.forEach(function (a) { a.classList.toggle("active", a.getAttribute("href") === "#" + id); });
      };
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { if (e.isIntersecting) setActive(e.target.id); });
      }, { rootMargin: "-80px 0px -70% 0px" });
      headings.forEach(function (h) { io.observe(h); });
    }
  }

  /* Barre de progression de lecture ------------------------------------------- */
  var bar = document.querySelector(".progress");
  if (bar && prose) {
    var ticking = false;
    var update = function () {
      var rect = prose.getBoundingClientRect();
      var total = rect.height - window.innerHeight * 0.6;
      var done = Math.min(1, Math.max(0, -rect.top / (total > 0 ? total : 1)));
      bar.style.transform = "scaleX(" + done + ")";
      ticking = false;
    };
    window.addEventListener("scroll", function () {
      if (!ticking) { window.requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    update();
  }

  /* Compteur de vues : une vue = au moins 5 s de lecture visible ------------------ */
  var beaconUrl = article.getAttribute("data-view-url");
  var csrf = article.getAttribute("data-csrf");
  if (beaconUrl && !article.hasAttribute("data-preview")) {
    var visibleMs = 0, last = Date.now(), sent = false;
    var tick = function () {
      var now = Date.now();
      if (document.visibilityState === "visible") visibleMs += now - last;
      last = now;
      if (!sent && visibleMs >= 5000) {
        sent = true;
        fetch(beaconUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": csrf, "X-Requested-With": "fetch" },
          keepalive: true
        }).catch(function () {});
      }
      if (!sent) setTimeout(tick, 1000);
    };
    document.addEventListener("visibilitychange", function () { last = Date.now(); });
    setTimeout(tick, 1000);
  }
})();
