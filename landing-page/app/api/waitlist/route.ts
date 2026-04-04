import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const { email } = await request.json();

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json(
      { error: "Please enter a valid email address." },
      { status: 400 }
    );
  }

  const apiKey = process.env.SENDGRID_API_KEY;
  const listId = process.env.SENDGRID_LIST_ID;

  if (!apiKey || !listId) {
    console.error("Missing SENDGRID_API_KEY or SENDGRID_LIST_ID");
    return NextResponse.json(
      { error: "Waitlist is temporarily unavailable." },
      { status: 500 }
    );
  }

  const response = await fetch(
    "https://api.sendgrid.com/v3/marketing/contacts",
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        list_ids: [listId],
        contacts: [{ email }],
      }),
    }
  );

  if (!response.ok) {
    const error = await response.text();
    console.error("SendGrid error:", error);
    return NextResponse.json(
      { error: "Something went wrong. Please try again." },
      { status: 500 }
    );
  }

  return NextResponse.json({ success: true });
}
