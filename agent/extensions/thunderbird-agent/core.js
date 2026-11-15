/* Fonctions pures partagées avec les tests Node. */
(function (root) {
  const excluded = new Set(["trash", "junk", "drafts", "outbox", "templates"]);
  function allowedFolder(folder) {
    return !(folder.specialUse || []).some(value => excluded.has(value)) && !excluded.has(folder.type);
  }
  function messageKey(accountId, folderId, message) {
    return [accountId, message.headerMessageId || folderId, message.date instanceof Date ? message.date.toISOString() : message.date,
      message.author, message.subject, message.size || 0].join("|");
  }
  function eligible(message) { return !message.junk; }
  const api = { allowedFolder, messageKey, eligible };
  root.AgentThunderbird = api;
  if (typeof module !== "undefined") module.exports = api;
})(globalThis);
