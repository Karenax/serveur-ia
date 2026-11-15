const { test } = require("node:test");
const assert = require("node:assert/strict");
const { allowedFolder, messageKey, eligible } = require("./core.js");
test("exclut junk, corbeille et leurs descendants par parcours", () => {
  assert.equal(allowedFolder({ type: "junk" }), false);
  assert.equal(allowedFolder({ specialUse: ["trash"] }), false);
  assert.equal(allowedFolder({ specialUse: ["sent"] }), true);
  assert.equal(eligible({ junk: true }), false);
});
test("clé de transmission indépendante du dossier pour les mails identifiés", () => {
  const message = { headerMessageId: "abc@example.org", date: new Date("2026-10-02"), subject: "Réponse", author: "a@b.fr", size: 123 };
  assert.equal(messageKey("account1", "inbox", message), messageKey("account1", "project", message));
  assert.notEqual(messageKey("account1", "inbox", message), messageKey("account2", "inbox", message));
});
