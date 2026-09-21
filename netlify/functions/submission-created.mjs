/**
 * Fires automatically whenever Netlify Forms accepts a submission.
 * Netlify stores every submission regardless, so if sending fails the
 * enquiry is never lost — it is still in Forms in the Netlify dashboard.
 *
 * Environment variables (Site configuration → Environment variables):
 *   BREVO_API_KEY   a Brevo v3 API key            ─┐ set one of these
 *   RESEND_API_KEY  a Resend API key              ─┘
 *   NOTIFY_TO       where enquiries land          (default hello@savidorhr.com)
 *   NOTIFY_FROM     the verified sender address   (default hello@savidorhr.com)
 */

const TO = process.env.NOTIFY_TO || "hello@savidorhr.com";
const FROM = process.env.NOTIFY_FROM || "hello@savidorhr.com";

const BRAND = "#A24212";
const INK = "#101828";
const INK_2 = "#475467";
const INK_3 = "#667085";
const LINE = "#E4E7EC";
const BG_2 = "#F9FAFB";

// Known fields in the order they should read in the email. Anything the form
// gains later still shows up, just after these, with its raw name as the label.
const LABELS = {
  first_name: "First name",
  last_name: "Last name",
  email: "Work email",
  company: "Company",
  headcount: "Headcount",
  interest: "Interested in",
  message: "What gives them the most trouble",
};

const esc = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

/** Orders the submitted fields: known ones first, then any extras. */
function orderedFields(data) {
  const known = Object.keys(LABELS).filter((k) => data[k]);
  const extra = Object.keys(data).filter(
    (k) => !(k in LABELS) && !k.startsWith("bot-") && k !== "form-name" && data[k]
  );
  // A multiple select arrives as an array. String() on one gives
  // "A,B,C" with no spaces, which reads badly in an email, so join it
  // properly rather than letting the default coercion decide.
  const show = (v) => (Array.isArray(v) ? v.join(", ") : String(v));
  return [...known, ...extra].map((k) => [LABELS[k] || k, show(data[k])]);
}

function buildHtml(data, meta) {
  const name = [data.first_name, data.last_name].filter(Boolean).join(" ") || "Someone";
  const company = data.company ? ` at ${data.company}` : "";

  const rows = orderedFields(data)
    .map(
      ([label, value]) => `
      <tr>
        <td style="padding:14px 0 0;vertical-align:top;width:180px;font:600 12px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;letter-spacing:.04em;text-transform:uppercase;color:${INK_3};">${esc(
        label
      )}</td>
        <td style="padding:14px 0 0;vertical-align:top;font:400 15px/1.65 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:${INK};white-space:pre-wrap;">${esc(
        value
      )}</td>
      </tr>`
    )
    .join("");

  return `<!doctype html>
<html><body style="margin:0;padding:0;background:${BG_2};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${BG_2};padding:32px 16px;">
 <tr><td align="center">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;background:#FFFFFF;border:1px solid ${LINE};border-radius:16px;overflow:hidden;">

   <tr><td style="background:${BRAND};padding:22px 32px;">
     <div style="font:800 17px/1.3 'Segoe UI',-apple-system,BlinkMacSystemFont,Roboto,sans-serif;color:#FFFFFF;letter-spacing:-.01em;">SavidorHR</div>
     <div style="font:500 13px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#F7E4D9;margin-top:2px;">New walkthrough request</div>
   </td></tr>

   <tr><td style="padding:30px 32px 4px;">
     <div style="font:700 20px/1.4 'Segoe UI',-apple-system,BlinkMacSystemFont,Roboto,sans-serif;color:${INK};letter-spacing:-.01em;">${esc(
    name
  )}${esc(company)}</div>
     <div style="font:400 14px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:${INK_2};margin-top:6px;">Reply to this email to answer them directly.</div>
   </td></tr>

   <tr><td style="padding:8px 32px 30px;">
     <table role="presentation" width="100%" cellpadding="0" cellspacing="0">${rows}</table>
   </td></tr>

   ${
     data.email
       ? `<tr><td style="padding:0 32px 32px;">
     <a href="mailto:${esc(data.email)}" style="display:inline-block;background:${BRAND};color:#FFFFFF;text-decoration:none;font:600 15px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:13px 22px;border-radius:10px;">Reply to ${esc(
           data.first_name || data.email
         )}</a>
   </td></tr>`
       : ""
   }

   <tr><td style="border-top:1px solid ${LINE};background:${BG_2};padding:18px 32px;font:400 12px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:${INK_3};">
     Sent from the contact form on savidorhr.com${
       meta.date ? ` &middot; ${esc(meta.date)}` : ""
     }<br>A copy is kept under Forms in the Netlify dashboard.
   </td></tr>

  </table>
 </td></tr>
</table>
</body></html>`;
}

function buildText(data) {
  return orderedFields(data)
    .map(([label, value]) => `${label}: ${value}`)
    .join("\n");
}

async function send({ subject, html, text, replyTo }) {
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
        replyTo: replyTo ? { email: replyTo } : undefined,
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
      body: JSON.stringify({
        from: `SavidorHR website <${FROM}>`,
        to: [TO],
        reply_to: replyTo || undefined,
        subject,
        html,
        text,
      }),
    });
    if (!res.ok) throw new Error(`Resend ${res.status}: ${await res.text()}`);
    return "resend";
  }

  throw new Error("No email provider key set (BREVO_API_KEY or RESEND_API_KEY).");
}

export const handler = async (event) => {
  let payload;
  try {
    ({ payload } = JSON.parse(event.body || "{}"));
  } catch {
    return { statusCode: 400, body: "Bad payload" };
  }
  if (!payload) return { statusCode: 400, body: "No payload" };

  const data = payload.data || {};
  const name = [data.first_name, data.last_name].filter(Boolean).join(" ").trim();
  const subject = `Walkthrough request${data.company ? ` — ${data.company}` : ""}${
    name ? ` (${name})` : ""
  }`;

  try {
    const via = await send({
      subject,
      html: buildHtml(data, { date: payload.created_at }),
      text: buildText(data),
      replyTo: data.email,
    });
    console.log(`Notification sent via ${via} for ${data.email || "unknown sender"}`);
    return { statusCode: 200, body: "sent" };
  } catch (err) {
    // Never fail loudly: the submission is already safe in Netlify Forms.
    console.error("Notification failed:", err.message);
    return { statusCode: 200, body: "stored, notification failed" };
  }
};
