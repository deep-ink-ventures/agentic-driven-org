/**
 * Platform registry — add new platforms here.
 *
 * Each entry maps a platform key to:
 *   - domains: array of cookie domains to extract from
 *   - match: regex tested against the active tab URL
 *   - label: display name in the popup
 *   - configKey: the key used in agent config (e.g. "twitter_session")
 */
const PLATFORMS = {
  twitter: {
    domains: [".x.com", ".twitter.com"],
    match: /x\.com|twitter\.com/,
    label: "Twitter / X",
    configKey: "twitter_session",
  },
  reddit: {
    domains: [".reddit.com"],
    match: /reddit\.com/,
    label: "Reddit",
    configKey: "reddit_session",
  },
  luma: {
    domains: [".lu.ma"],
    match: /lu\.ma/,
    label: "Lu.ma",
    configKey: "luma_session",
  },
};

// Also export for module usage if needed
if (typeof module !== "undefined") module.exports = PLATFORMS;
