import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET(request: NextRequest) {
  const dataset = request.nextUrl.searchParams.get("dataset")?.trim() ?? "";
  const series = request.nextUrl.searchParams.get("series")?.trim() ?? "";
  const limit = Number(request.nextUrl.searchParams.get("limit") ?? "120");

  if (!dataset || !series || dataset.length > 200 || series.length > 200) {
    return NextResponse.json(
      { status: "invalid_request", message: "Choose a dataset and series before requesting observations." },
      { status: 400, headers: { "Cache-Control": "no-store" } }
    );
  }

  if (!Number.isInteger(limit) || limit < 1 || limit > 5000) {
    return NextResponse.json(
      { status: "invalid_request", message: "The observation limit must be between 1 and 5,000." },
      { status: 400, headers: { "Cache-Control": "no-store" } }
    );
  }

  const baseUrl = process.env.DATA_API_URL?.replace(/\/$/, "");
  const token = process.env.DATA_API_TOKEN;

  if (!baseUrl || !token) {
    return NextResponse.json(
      { status: "not_configured", message: "The research data service has not been connected yet." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }

  try {
    const upstreamUrl = new URL(`${baseUrl}/v1/observations`);
    upstreamUrl.searchParams.set("dataset", dataset);
    upstreamUrl.searchParams.set("series_name", series);
    upstreamUrl.searchParams.set("limit", String(limit));

    const response = await fetch(upstreamUrl, {
      cache: "no-store",
      headers: { "Accept": "application/json", "Authorization": `Bearer ${token}` },
      signal: AbortSignal.timeout(8000)
    });

    if (!response.ok) {
      return NextResponse.json(
        { status: "unavailable", message: "The selected series is temporarily unavailable." },
        { status: 503, headers: { "Cache-Control": "no-store" } }
      );
    }

    const observations = await response.json();
    return NextResponse.json(
      { status: "ok", market_series: observations },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch {
    return NextResponse.json(
      { status: "unavailable", message: "The selected series could not be retrieved." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}
