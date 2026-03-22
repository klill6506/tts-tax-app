/**
 * PDF.js-based PDF viewer with continuous scroll, custom toolbar,
 * and sidebar page navigation integration.
 *
 * Renders PDF pages to canvas elements with virtual rendering
 * (only visible pages + buffer are rendered at full quality).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface PdfViewerProps {
  /** PDF data as Uint8Array or ArrayBuffer */
  data: Uint8Array | ArrayBuffer | null;
  /** Callback when the visible page changes (1-indexed) */
  onPageChange?: (page: number) => void;
  /** Imperatively scroll to this page (1-indexed). Changes trigger scroll. */
  goToPage?: number;
}

const SCALE_STEP = 0.15;
const MIN_SCALE = 0.5;
const MAX_SCALE = 3.0;
const BUFFER_PAGES = 2; // render this many pages above/below viewport
const PAGE_GAP = 8; // px between pages

export default function PdfViewer({ data, onPageChange, goToPage }: PdfViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pdf, setPdf] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(0); // 0 = fit-to-width (computed)
  const [fitScale, setFitScale] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track which pages are rendered to avoid re-rendering
  const renderedPages = useRef<Map<number, number>>(new Map()); // page -> scale
  const canvasRefs = useRef<Map<number, HTMLCanvasElement>>(new Map());
  const pageHeights = useRef<number[]>([]);

  // Load PDF document
  useEffect(() => {
    if (!data) {
      setPdf(null);
      setNumPages(0);
      return;
    }

    setLoading(true);
    setError(null);
    renderedPages.current.clear();

    const loadingTask = pdfjsLib.getDocument({ data });
    loadingTask.promise
      .then((doc) => {
        setPdf(doc);
        setNumPages(doc.numPages);
        setCurrentPage(1);
        setLoading(false);
      })
      .catch((err) => {
        setError(`Failed to load PDF: ${err.message}`);
        setLoading(false);
      });

    return () => {
      loadingTask.destroy();
    };
  }, [data]);

  // Compute fit-to-width scale when PDF loads or container resizes
  useEffect(() => {
    if (!pdf || !containerRef.current) return;

    async function computeFitScale() {
      const page = await pdf!.getPage(1);
      const viewport = page.getViewport({ scale: 1 });
      const containerWidth = containerRef.current!.clientWidth - 32; // 16px padding each side
      const computed = containerWidth / viewport.width;
      setFitScale(computed);
      if (scale === 0) setScale(computed);
    }

    computeFitScale();

    const observer = new ResizeObserver(() => {
      computeFitScale();
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [pdf]);

  const effectiveScale = scale || fitScale;

  // Render visible pages
  const renderVisiblePages = useCallback(async () => {
    if (!pdf || !containerRef.current) return;

    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    const viewHeight = container.clientHeight;

    // Determine which pages are visible
    let accHeight = 0;
    let firstVisible = 1;
    let lastVisible = numPages;

    for (let i = 0; i < numPages; i++) {
      const h = pageHeights.current[i] || 0;
      if (accHeight + h < scrollTop) {
        firstVisible = i + 2; // next page is first visible
      }
      if (accHeight > scrollTop + viewHeight) {
        lastVisible = i;
        break;
      }
      accHeight += h + PAGE_GAP;
    }

    // Add buffer
    const renderStart = Math.max(1, firstVisible - BUFFER_PAGES);
    const renderEnd = Math.min(numPages, lastVisible + BUFFER_PAGES);

    // Update current page (the one most visible)
    if (firstVisible !== currentPage) {
      setCurrentPage(Math.min(firstVisible, numPages));
      onPageChange?.(Math.min(firstVisible, numPages));
    }

    // Render each page that needs it
    for (let pageNum = renderStart; pageNum <= renderEnd; pageNum++) {
      const prevScale = renderedPages.current.get(pageNum);
      if (prevScale === effectiveScale) continue; // already rendered at this scale

      const canvas = canvasRefs.current.get(pageNum);
      if (!canvas) continue;

      try {
        const page = await pdf.getPage(pageNum);
        const viewport = page.getViewport({ scale: effectiveScale });

        const dpr = window.devicePixelRatio || 1;
        canvas.width = viewport.width * dpr;
        canvas.height = viewport.height * dpr;
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;

        const ctx = canvas.getContext("2d")!;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        await page.render({ canvasContext: ctx, viewport }).promise;
        renderedPages.current.set(pageNum, effectiveScale);
      } catch {
        // Page may have been cleaned up during navigation
      }
    }
  }, [pdf, numPages, effectiveScale, currentPage, onPageChange]);

  // Set up page placeholders with correct heights
  useEffect(() => {
    if (!pdf) return;

    async function setupPages() {
      const heights: number[] = [];
      for (let i = 1; i <= pdf!.numPages; i++) {
        const page = await pdf!.getPage(i);
        const viewport = page.getViewport({ scale: effectiveScale });
        heights.push(viewport.height);
      }
      pageHeights.current = heights;
      renderedPages.current.clear(); // re-render at new scale
      renderVisiblePages();
    }

    setupPages();
  }, [pdf, effectiveScale]);

  // Scroll listener
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let ticking = false;
    function onScroll() {
      if (!ticking) {
        requestAnimationFrame(() => {
          renderVisiblePages();
          ticking = false;
        });
        ticking = true;
      }
    }

    container.addEventListener("scroll", onScroll, { passive: true });
    return () => container.removeEventListener("scroll", onScroll);
  }, [renderVisiblePages]);

  // Handle goToPage prop changes
  useEffect(() => {
    if (!goToPage || !containerRef.current || !pdf) return;

    let offset = 0;
    for (let i = 0; i < goToPage - 1 && i < pageHeights.current.length; i++) {
      offset += pageHeights.current[i] + PAGE_GAP;
    }
    containerRef.current.scrollTo({ top: offset, behavior: "smooth" });
  }, [goToPage, pdf]);

  // Zoom controls
  function zoomIn() {
    setScale((s) => Math.min((s || fitScale) + SCALE_STEP, MAX_SCALE));
  }
  function zoomOut() {
    setScale((s) => Math.max((s || fitScale) - SCALE_STEP, MIN_SCALE));
  }
  function zoomFit() {
    setScale(0); // reset to fit-to-width
  }

  const pctLabel = Math.round(effectiveScale * 100);

  // Download the PDF
  function handleDownload() {
    if (!data) return;
    const blob = new Blob([data], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "tax_return.pdf";
    a.click();
    URL.revokeObjectURL(url);
  }

  // Print
  function handlePrint() {
    if (!data) return;
    const blob = new Blob([data], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const w = window.open(url);
    if (w) {
      w.addEventListener("load", () => {
        w.print();
      });
    }
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-4 border-primary-subtle border-t-primary" />
          <p className="text-sm text-tx-secondary">Loading PDF...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-danger">{error}</p>
      </div>
    );
  }

  if (!pdf) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-tx-muted">No PDF loaded</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col min-h-0">
      {/* Custom toolbar */}
      <div className="flex items-center justify-between border-b border-border bg-card px-3 py-1 shrink-0">
        {/* Page navigation */}
        <div className="flex items-center gap-1 text-xs text-tx-secondary">
          <button
            onClick={() => {
              const prev = Math.max(1, currentPage - 1);
              containerRef.current?.scrollTo({
                top: pageHeights.current.slice(0, prev - 1).reduce((a, b) => a + b + PAGE_GAP, 0),
                behavior: "smooth",
              });
            }}
            disabled={currentPage <= 1}
            className="rounded px-1.5 py-0.5 hover:bg-surface-alt disabled:opacity-30"
          >
            &#9664;
          </button>
          <span className="tabular-nums">
            Page {currentPage} of {numPages}
          </span>
          <button
            onClick={() => {
              const next = Math.min(numPages, currentPage + 1);
              containerRef.current?.scrollTo({
                top: pageHeights.current.slice(0, next - 1).reduce((a, b) => a + b + PAGE_GAP, 0),
                behavior: "smooth",
              });
            }}
            disabled={currentPage >= numPages}
            className="rounded px-1.5 py-0.5 hover:bg-surface-alt disabled:opacity-30"
          >
            &#9654;
          </button>
        </div>

        {/* Zoom controls */}
        <div className="flex items-center gap-1 text-xs">
          <button onClick={zoomOut} className="rounded px-1.5 py-0.5 text-tx-secondary hover:bg-surface-alt">
            &minus;
          </button>
          <button
            onClick={zoomFit}
            className="rounded px-2 py-0.5 tabular-nums text-tx-secondary hover:bg-surface-alt"
            title="Fit to width"
          >
            {pctLabel}%
          </button>
          <button onClick={zoomIn} className="rounded px-1.5 py-0.5 text-tx-secondary hover:bg-surface-alt">
            +
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          <button
            onClick={handlePrint}
            className="rounded px-2 py-0.5 text-xs text-tx-secondary hover:bg-surface-alt"
            title="Print"
          >
            Print
          </button>
          <button
            onClick={handleDownload}
            className="rounded bg-primary px-2 py-0.5 text-xs text-white hover:bg-primary-hover"
            title="Download"
          >
            Download
          </button>
        </div>
      </div>

      {/* Scrollable page container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto bg-neutral-200 dark:bg-neutral-800"
        style={{ paddingTop: PAGE_GAP, paddingBottom: PAGE_GAP }}
      >
        <div className="flex flex-col items-center" style={{ gap: PAGE_GAP }}>
          {Array.from({ length: numPages }, (_, i) => {
            const pageNum = i + 1;
            const h = pageHeights.current[i] || 792; // fallback height
            return (
              <canvas
                key={pageNum}
                ref={(el) => {
                  if (el) canvasRefs.current.set(pageNum, el);
                  else canvasRefs.current.delete(pageNum);
                }}
                style={{
                  width: "100%",
                  maxWidth: `${612 * effectiveScale}px`,
                  height: `${h}px`,
                  boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                  backgroundColor: "white",
                }}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
