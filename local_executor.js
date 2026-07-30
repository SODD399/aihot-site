const fs = require("fs");
const path = require("path");
const readline = require("readline");

let chromium;
try {
  ({ chromium } = require("playwright"));
} catch (err) {
  console.error("Playwright is not available. Run through local_executor.bat in Codex, or install Playwright locally.");
  process.exit(1);
}

const ROOT = __dirname;
const DB_PATH = path.join(ROOT, "data", "db.json");
const OUT_DIR = path.join(ROOT, "data", "executor");
const PROFILE_DIR = path.join(ROOT, ".local-douyin-profile");
const CHROME_EXE = "C:/Program Files/Google/Chrome/Application/chrome.exe";

function argValue(name, fallback = "") {
  const idx = process.argv.indexOf(`--${name}`);
  return idx >= 0 && process.argv[idx + 1] ? process.argv[idx + 1] : fallback;
}

function modeArg() {
  const mode = process.argv[2] || "login";
  return mode.startsWith("--") ? "login" : mode;
}

function readDb() {
  if (!fs.existsSync(DB_PATH)) return {};
  return JSON.parse(fs.readFileSync(DB_PATH, "utf8"));
}

function latestPublishTask(account) {
  const db = readDb();
  const tasks = (((db || {}).automation || {}).publish_tasks || []);
  return tasks.find((task) => !account || task.account === account) || null;
}

function ensureOutDir() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
}

function waitForEnter(message) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => rl.question(message, () => {
    rl.close();
    resolve();
  }));
}

function writePublishPackage(task) {
  ensureOutDir();
  const body = [
    `账号：${task.account || ""}`,
    `标题：${task.title || ""}`,
    `视频路径：${task.video_path || ""}`,
    `计划时间：${task.scheduled_at || "待定"}`,
    "",
    "发布文案：",
    task.caption || "",
    "",
    "Tag：",
    task.tags || "",
    "",
    "封面说明：",
    task.cover_note || "",
  ].join("\n");
  const file = path.join(OUT_DIR, `publish-package-${timestamp()}.txt`);
  fs.writeFileSync(file, body, "utf8");
  return file;
}

async function openContext() {
  const launchOptions = {
    headless: false,
    viewport: { width: 1366, height: 900 },
  };
  if (fs.existsSync(CHROME_EXE)) {
    launchOptions.executablePath = CHROME_EXE;
  }
  return chromium.launchPersistentContext(PROFILE_DIR, launchOptions);
}

async function run() {
  const mode = modeArg();
  const account = argValue("account", "");
  const url = argValue("url", "");
  const context = await openContext();
  const page = context.pages()[0] || await context.newPage();

  if (mode === "publish") {
    const task = latestPublishTask(account);
    if (task) {
      const file = writePublishPackage(task);
      console.log(`Publish package written: ${file}`);
      console.log("Open that txt file beside the browser if you need to copy fields.");
    } else {
      console.log(`No publish task found for account: ${account || "any"}`);
    }
    await page.goto(url || "https://creator.douyin.com/creator-micro/content/upload", { waitUntil: "domcontentloaded" });
    console.log("Upload page opened. Log in or switch account if Douyin asks.");
    console.log("This first executor version stops before final publish. You confirm the final action.");
    await waitForEnter("Press Enter here after you finish checking the page...");
  } else if (mode === "comments") {
    await page.goto(url || "https://creator.douyin.com/", { waitUntil: "domcontentloaded" });
    console.log("Creator center opened. Navigate to the target work/comment page and scroll comments into view.");
    await waitForEnter("Press Enter here after comments are visible in the browser...");
    const visibleText = await page.evaluate(() => document.body ? document.body.innerText : "");
    ensureOutDir();
    const file = path.join(OUT_DIR, `douyin-visible-text-${timestamp()}.txt`);
    fs.writeFileSync(file, visibleText, "utf8");
    console.log(`Visible page text saved: ${file}`);
    console.log("Open the txt, copy the comment lines into the website's 评论监测 import box.");
  } else {
    await page.goto(url || "https://creator.douyin.com/", { waitUntil: "domcontentloaded" });
    console.log(`Douyin creator center opened for local mode. Account label: ${account || "not specified"}`);
    console.log("Log in in this Chrome window. The local profile is stored only on this computer.");
    await waitForEnter("Press Enter here when login/check is done...");
  }

  await context.close();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
