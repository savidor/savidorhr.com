/**
 * Diagnose the contact-form email pipeline from a browser.
 *
 * The form itself can never tell you it is broken. Netlify stores every
 * submission whatever happens, and submission-created.mjs deliberately
 * swallows send failures so an enquiry is never lost, which means a missing
 * API key, an unverified sender and a destination that cannot receive mail all
 * look identical from outside: the visitor gets the thank you page and nothing
 * arrives. This endpoint makes the difference visible.
 *
 *   GET /.netlify/functions/notify-check
 *     Reports the configuration and the DNS underneath it. Addresses are
 *     masked, so it is safe to open without leaking an inbox to whoever finds
 *     the URL.
 *
 *   GET /.netlify/functions/notify-check?send=<CHECK_TOKEN>
 *     Also sends one real test email to NOTIFY_TO. The destination is always
 *     NOTIFY_TO and never anything from the query string, so this cannot be
 *     pointed at a stranger. The token only stops it being used to flood the
 *     owner's own inbox. Set CHECK_TOKEN in the Netlify dashboard.
 */

import { promises as dns } from "node:dns";

const TO = process.env.NOTIFY_TO || "tochukwu.nwaiwu20@gmail.com";
const FROM = process.env.NOTIFY_FROM || "hello@savidorhr.com";

/** t***u@gmail.com, so the report can be read without exposing the address. */
function mask(addr) {
  const [user, domain] = String(addr).split("@");
  if (!domain) return "(not an address)";
  const u = user.length <= 2 ? user[0] + "*" : user[0] + "***" + user.slice(-1);
  return `${u}@${domain}`;
}

const domainOf = (addr) => String(addr).split("@")[1] || "";

async function mx(domain) {
  try {
    const r = await dns.resolveMx(domain);
    return r.length ? r.map((m) => `${m.priority} ${m.exchange}`) : [];
  } catch {
    return [];
  }
}

async function txt(domain) {
  try {
    return (await dns.resolveTxt(domain)).map((c) => c.join(""));
  } catch {
    return [];
  }
}

async function report() {
  const provider = process.env.BREVO_API_KEY
    ? "brevo"
    : process.env.RESEND_API_KEY
    ? "resend"
    : null;

  const toDomain = domainOf(TO);
  const fromDomain = domainOf(FROM);

  const toMx = await mx(toDomain);
  const fromTxt = await txt(fromDomain);
  const spf = fromTxt.filter((t) => t.toLowerCase().startsWith("v=spf1"));
  const dmarc = await txt(`_dmarc.${fromDomain}`);

  const problems = [];
  if (!provider) {
    problems.push(
      "No sending key is set, so nothing is ever sent. Set BREVO_API_KEY or " +
        "RESEND_API_KEY in Site configuration, Environment variables."
    );
  }
  if (!toMx.length) {
    problems.push(
      `The destination domain ${toDomain} publishes no MX record, so mail to it ` +
        `cannot be delivered by anyone. Point NOTIFY_TO at an inbox that can ` +
        `actually receive, or add MX records for ${toDomain}.`
    );
  }
  if (!spf.length) {
    problems.push(
      `${fromDomain} publishes no SPF record. A provider will usually refuse to ` +
        `send as an unverified domain, and anything that does go out is likely ` +
        `to be filtered. Verify ${fromDomain} with the provider and add the SPF ` +
        `and DKIM records it gives you, or set NOTIFY_FROM to an address you ` +
        `have already verified.`
    );
  }

  return {
    checked_at: new Date().toISOString(),
    provider_key_set: provider || "none",
    notify_to: mask(TO),
    notify_from: mask(FROM),
    destination_can_receive: toMx.length > 0,
    destination_mx: toMx,
    sender_domain_spf: spf,
    sender_domain_dmarc: dmarc,
    verdict: problems.length ? "WILL NOT WORK" : "configuration looks deliverable",
    problems,
  };
}

async function sendTest() {
  const subject = "SavidorHR contact form test";
  const html =
    `<p>This is a test from <code>notify-check</code> on the SavidorHR site.</p>` +
    `<p>If you are reading it, the contact form can reach this inbox: a real ` +
    `enquiry will arrive the same way, with Reply-To set to the person who sent it.</p>` +
    `<p>Sent ${new Date().toUTCString()}.</p>`;
  const text = "Test from notify-check. If you can read this, the contact form can reach this inbox.";

  if (process.env.BREVO_API_KEY) {
    const res = await fetch("https://api.brevo.com/v3/smtp/email", {
      method: "POST",
      headers: {
        "api-key": process.env.BREVO_API_KEY,
        "content-type": "application/json",
        accept: "application/json",
      },
      body: JSON.stringify({
        sender: { email: FROM, name: "SavidorHR website" },
        to: [{ email: TO }],
        subject,
        htmlContent: html,
        textContent: text,
      }),
    });
    if (!res.ok) throw new Error(`Brevo ${res.status}: ${await res.text()}`);
    return "brevo";
  }
  if (process.env.RESEND_API_KEY) {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        authorization: `Bearer ${process.env.RESEND_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ from: `SavidorHR website <${FROM}>`, to: [TO], subject, html, text }),
    });
    if (!res.ok) throw new Error(`Resend ${res.status}: ${await res.text()}`);
    return "resend";
  }
  throw new Error("No email provider key set (BREVO_API_KEY or RESEND_API_KEY).");
}

export const handler = async (event) => {
  const out = await report();
  const asked = (event.queryStringParameters || {}).send;

  if (asked) {
    const token = process.env.CHECK_TOKEN;
    if (!token) {
      out.test_send = "refused: CHECK_TOKEN is not set on the site, so test sending is disabled.";
    } else if (asked !== token) {
      out.test_send = "refused: wrong token.";
    } else {
      try {
        out.test_send = `sent via ${await sendTest()} to ${mask(TO)}. Check that inbox, including spam.`;
      } catch (err) {
        out.test_send = `failed: ${err.message}`;
      }
    }
  }

  return {
    statusCode: 200,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
    body: JSON.stringify(out, null, 2),
  };
};
