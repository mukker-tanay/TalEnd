import React, { useState, useEffect } from "react";

// Types for both Dashboard and Search CVs
export type CVType = {
  _id: string;
  original_filename: string;
  stored_filename: string;
  // Optional fields for search
  name?: string;
  current_position?: string;
  total_experience_years?: number;
  skills?: string[];
  match_score?: number;
};

type CVSliderProps = {
  cvList: CVType[];
  initialIndex: number;
  onClose: () => void;
};

const CVSlider: React.FC<CVSliderProps> = ({ cvList, initialIndex, onClose }) => {
  const [current, setCurrent] = useState(initialIndex);

  useEffect(() => {
    setCurrent(initialIndex);
  }, [initialIndex, cvList]);

  if (!cvList.length) return null;
  const cv = cvList[current];
  const embedUrl = cv?.stored_filename ? `http://localhost:8000/cv/preview/${cv.stored_filename}` : '';
  console.log("CVSlider cv:", cv);
  console.log("Embed URL:", embedUrl);

  if (!cv) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 z-40 flex justify-end">
        <div className="h-full bg-white shadow-lg border-l border-gray-300 flex flex-col z-50 animate-slide-in-right"
          style={{ width: "40vw", maxWidth: 700, minWidth: 320 }}
        >
          <div className="flex-1 flex items-center justify-center">
            <span className="text-red-600">No CV data found for this index.</span>
          </div>
        </div>
      </div>
    );
  }

  const goPrev = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrent((prev) => (prev > 0 ? prev - 1 : prev));
  };
  const goNext = (e: React.MouseEvent) => {
    e.stopPropagation();
    setCurrent((prev) => (prev < cvList.length - 1 ? prev + 1 : prev));
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 z-40 flex justify-end"
      onClick={onClose}
    >
      <div
        className="h-full bg-white shadow-lg border-l border-gray-300 flex flex-col z-50 animate-slide-in-right"
        style={{ width: "40vw", maxWidth: 700, minWidth: 320 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center px-4 py-3 border-b">
          <h3 className="text-lg font-semibold truncate" title={cv.original_filename}>
            {cv.original_filename}
          </h3>
          <button onClick={onClose} className="text-gray-600 hover:text-black text-xl">×</button>
        </div>
        <div className="flex-1 overflow-auto p-4 flex flex-col items-center">
          {cv.stored_filename.endsWith(".pdf") ? (
            <embed
              src={embedUrl}
              type="application/pdf"
              width="100%"
              height="600px"
              className="rounded border"
            />
          ) : (
            <p className="text-sm text-gray-600">
              Preview not available for DOC/DOCX. Please download.
            </p>
          )}
        </div>
        <div className="flex items-center justify-between px-4 py-2 border-t">
          <button
            onClick={goPrev}
            disabled={current === 0}
            className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300 disabled:opacity-50"
          >
            ◀ Prev
          </button>
          <span className="text-sm text-gray-500">
            {current + 1} / {cvList.length}
          </span>
          <button
            onClick={goNext}
            disabled={current === cvList.length - 1}
            className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300 disabled:opacity-50"
          >
            Next ▶
          </button>
        </div>
        <div className="p-4 border-t">
          <a
            href={`http://localhost:8000/cv/download/${cv.stored_filename}`}
            target="_blank"
            rel="noopener noreferrer"
            download
          >
            <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 w-full">
              Download
            </button>
          </a>
        </div>
      </div>
    </div>
  );
};

export default CVSlider; 