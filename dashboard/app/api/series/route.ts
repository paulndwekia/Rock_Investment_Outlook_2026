import { NextRequest, NextResponse } from "next/server";
import { fetchPDMOPublicData } from "@/lib/public-data";

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

  if (baseUrl && token) {
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
      if (response.ok) {
        const observations = await response.json();
        return NextResponse.json({ status: "ok", market_series: observations }, { headers: { "Cache-Control": "no-store" } });
      }
    } catch {
      // Fall through to the official public Treasury feeds.
    }
  }

  try {
    const { observations, available_series } = await fetchPDMOPublicData();
    const selected = available_series.find((item) => item.dataset === dataset && item.series === series);
    if (!selected) {
      return NextResponse.json(
        { status: "not_found", message: "That dataset and series are not available in the current public Treasury feeds." },
        { status: 404, headers: { "Cache-Control": "no-store" } }
      );
    }

    const rows = observations
      .filter((item) => item.dataset === dataset && item.series === series)
      .slice(-limit);
    return NextResponse.json(
      { status: "ok", market_series: rows },
      { headers: { "Cache-Control": "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400" } }
    );
  } catch {
    return NextResponse.json(
      { status: "unavailable", message: "The selected public data series could not be retrieved." },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}
