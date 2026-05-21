// fb_phone.js — Phone number extraction from Facebook post text
// Handles: Malaysian mobile (01x/+60), Unicode-bold digits, spaced digits, WhatsApp prefixes

function extractPhone(text) {
  // Normalize common unicode digit variants to ASCII
  const unicodeMap = {
    '\uD835\uDFCE': '0', '\uD835\uDFCF': '1', '\uD835\uDFD0': '2', '\uD835\uDFD1': '3', '\uD835\uDFD2': '4',
    '\uD835\uDFD3': '5', '\uD835\uDFD4': '6', '\uD835\uDFD5': '7', '\uD835\uDFD6': '8', '\uD835\uDFD7': '9',
    '\uFF10': '0', '\uFF11': '1', '\uFF12': '2', '\uFF13': '3', '\uFF14': '4',
    '\uFF15': '5', '\uFF16': '6', '\uFF17': '7', '\uFF18': '8', '\uFF19': '9',
  };
  let normalized = text;
  for (const [u, a] of Object.entries(unicodeMap)) {
    normalized = normalized.split(u).join(a);
  }

  const patterns = [
    // Malaysian mobile: 01x-xxx xxxx or 01xxxxxxxx
    /01[0-9][- ]?[0-9]{3,4}[- ]?[0-9]{3,4}/g,
    // +60 with optional space/hyphen after country code
    /\+60[- ]?[0-9]{1,2}[- ]?[0-9]{3,4}[- ]?[0-9]{3,4}/g,
    // 60 without + (e.g. "60 11-2736 5970") — no digit directly before
    /(?<![0-9+])60[- ]?[0-9]{1,2}[- ]?[0-9]{3,4}[- ]?[0-9]{3,4}/g,
    // WhatsApp/whatapps/wasap/watsapp + digits
    /(?:whatsapp|whatapps|wasap|watsapp)[^0-9]*(\d{7,11})/gi,
    // Spaced-out digits: "0 1 8 7 8 8 4 7 6  6"
    /[0-9](?:\s*[0-9]\s*){6,14}[0-9]/g,
  ];

  const phones = new Set();
  for (const p of patterns) {
    let m;
    while ((m = p.exec(normalized)) !== null) {
      let ph = (m[1] || m[0]).replace(/[^0-9+]/g, '');
      // For spaced-digit pattern, collapse spaces
      if (ph.length < 9) {
        ph = m[0].replace(/\s+/g, '').replace(/[^0-9+]/g, '');
      }
      if (ph.length >= 9 && ph.length <= 15) phones.add(ph);
    }
  }
  return [...phones].join(', ');
}

module.exports = { extractPhone };
