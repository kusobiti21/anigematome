/*
 * ============================================================
 * 独自コメント欄 (Firebase Firestore使用)
 * ============================================================
 * 【事前準備】
 * 1. https://console.firebase.google.com で無料プロジェクトを作成
 * 2. 左メニュー「Firestore Database」→「データベースを作成」
 *    (本番環境モードでOK。リージョンは asia-northeast1 推奨)
 * 3. 左メニュー「プロジェクトの設定」→ 下の方の「マイアプリ」で
 *    ウェブアプリを追加すると、firebaseConfig が発行される
 * 4. 発行された値を、下の FIREBASE_CONFIG に書き写す
 * 5. Firestoreの「ルール」タブに、このファイルと同じ場所にある
 *    firestore.rules の内容を貼り付けて公開する
 * ============================================================
 */

import { initializeApp } from "https://www.gstatic.com/firebasejs/12.10.0/firebase-app.js";
import {
  getFirestore, collection, addDoc, query, where,
  orderBy, onSnapshot, serverTimestamp
} from "https://www.gstatic.com/firebasejs/12.10.0/firebase-firestore.js";

// TODO: ここをFirebaseコンソールで発行された自分の設定値に書き換える
const FIREBASE_CONFIG = {
  apiKey: "AIzaSyBp04M7zWSiz7ULNELMI-c1Q2pjozaDs7M",
  authDomain: "anigematome.firebaseapp.com",
  projectId: "anigematome",
  storageBucket: "anigematome.firebasestorage.app",
  messagingSenderId: "2512702471",
  appId: "1:2512702471:web:1d85a304ddeea18e816ea2"
};

const MAX_NAME_LENGTH = 30;
const MAX_TEXT_LENGTH = 500;
const ANON_NAME = window.ANON_NAME || "名無しさん";

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.textContent;
}

function formatTimestamp(ts) {
  if (!ts) return "";
  const d = ts.toDate ? ts.toDate() : new Date(ts);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function initComments(articleId) {
  const app = initializeApp(FIREBASE_CONFIG);
  const db = getFirestore(app);
  const commentsRef = collection(db, "comments");

  const listEl = document.getElementById("commentList");
  const countEl = document.getElementById("commentCount");
  const formEl = document.getElementById("commentForm");
  const nameInput = document.getElementById("commentName");
  const textInput = document.getElementById("commentText");
  const submitBtn = document.getElementById("commentSubmit");
  const statusEl = document.getElementById("commentStatus");

  if (!listEl || !formEl) return;

  // Firebase未設定の場合は案内を出して終了
  if (FIREBASE_CONFIG.apiKey === "YOUR_API_KEY") {
    listEl.innerHTML = '<div class="comment-empty">コメント機能は現在準備中です(サイト管理者による設定待ち)。</div>';
    formEl.style.display = "none";
    return;
  }

  const q = query(
    commentsRef,
    where("article", "==", articleId),
    orderBy("createdAt", "asc")
  );

  onSnapshot(q, (snapshot) => {
    if (snapshot.empty) {
      listEl.innerHTML = '<div class="comment-empty">まだコメントはありません。最初のコメントを書いてみませんか？</div>';
      if (countEl) countEl.textContent = "0";
      return;
    }

    let html = "";
    let i = 1;
    snapshot.forEach((doc) => {
      const c = doc.data();
      const name = escapeHtml(c.name || ANON_NAME);
      const text = escapeHtml(c.text || "").replace(/\n/g, "<br>");
      const time = formatTimestamp(c.createdAt);
      html += `
        <div class="res comment-item">
          <span class="res-no">${i}</span><span class="comment-name">${name}</span>
          <span class="comment-time">${time}</span>
          <div class="comment-body">${text}</div>
        </div>`;
      i++;
    });
    listEl.innerHTML = html;
    if (countEl) countEl.textContent = String(i - 1);
  }, (err) => {
    console.error("コメント読み込みエラー:", err);
    listEl.innerHTML = '<div class="comment-empty">コメントの読み込みに失敗しました。</div>';
  });

  formEl.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = (nameInput.value || ANON_NAME).trim().slice(0, MAX_NAME_LENGTH) || ANON_NAME;
    const text = (textInput.value || "").trim().slice(0, MAX_TEXT_LENGTH);

    if (!text) {
      if (statusEl) statusEl.textContent = "コメント内容を入力してください。";
      return;
    }

    submitBtn.disabled = true;
    if (statusEl) statusEl.textContent = "投稿中…";

    try {
      await addDoc(commentsRef, {
        article: articleId,
        name,
        text,
        createdAt: serverTimestamp()
      });
      textInput.value = "";
      if (statusEl) statusEl.textContent = "投稿しました！";
      setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 2500);
    } catch (err) {
      console.error("投稿エラー:", err);
      if (statusEl) statusEl.textContent = "投稿に失敗しました。時間をおいて再度お試しください。";
    } finally {
      submitBtn.disabled = false;
    }
  });
}

// 各記事ページで <script>window.ARTICLE_ID = "article1";</script> のように
// 先に定義しておくと、そのページ用のコメント欄として動作する
if (window.ARTICLE_ID) {
  initComments(window.ARTICLE_ID);
}
