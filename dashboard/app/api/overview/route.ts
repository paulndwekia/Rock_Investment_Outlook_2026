import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  const baseUrl = process.env.DATA_API_URL?.replace(/\/$/, "");
  const token = process.env.DATA_API_TOKEN;

  if (!baseUrl || !token) {
    return NextResponse.json({
      status: "not_configured",
      message: "The research data service has not been connected yet. No market figures are being simulated."
    }, { status: 200, headers: { "Cache-Control": "no-store" } });
  }

  try {
    const response = await fetch(`${baseUrl}/v1/overview`, {
      cache: "no-store",
      headers: { "Accept": "application/json", "Authorization": `Bearer ${token}` },
      signal: AbortSignal.timeout(8000)
    });
    if (!response.ok) {
      return NextResponse.json({
        status: "unavailable",
        message: "The data service is temporarily unavailable. Please try again later."
      }, { status: 200, headers: { "Cache-Control": "no-store" } });
    }
    const payload = await response.json();
    return NextResponse.json(payload, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({
      status: "unavailable",
      message: "The data service could not be reached. Market figures are hidden until a verified connection is available."
    }, { status: 200, headers: { "Cache-Control": "no-store" } });
  }
}