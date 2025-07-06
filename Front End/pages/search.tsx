import { useState } from "react";
import CVSlider, { CVType } from "../components/CVSlider";

type SearchResult = {
  _id: string;
  name: string;
  current_position: string;
  total_experience_years: number;
  skills: string[];
  match_score: number;
  stored_filename: string;
  original_filename: string;
};

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCV, setSelectedCV] = useState<SearchResult | null>(null);
  const [sliderOpen, setSliderOpen] = useState(false);
  const [sliderIndex, setSliderIndex] = useState(0);

  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(
        `http://localhost:8000/search-cvs?query=${encodeURIComponent(query)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await res.json();
      setResults(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Search error:", err);
    }
    setLoading(false);
  };

  const closePanel = () => {
    setSelectedCV(null);
  };

  const openSlider = (cv: SearchResult) => {
    const idx = results.findIndex((item) => item._id === cv._id);
    setSliderIndex(idx);
    setSliderOpen(true);
  };

  return (
    <div className="min-h-screen px-6 py-10 bg-gray-100 relative">
      <h1 className="text-3xl font-bold mb-6">CV Search</h1>

      <form onSubmit={handleSearch} className="flex gap-2 mb-8">
        <input
          type="text"
          placeholder="Search by keyword (e.g., React, Python, SQL)"
          className="flex-grow px-4 py-2 border rounded"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          required
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {results.length === 0 && !loading && (
        <p className="text-gray-500 text-sm">No results yet.</p>
      )}

      {results.length > 0 && (
        <div className="bg-white shadow-md rounded overflow-x-auto max-w-6xl">
          <table className="w-full text-sm text-left border-collapse">
            <thead className="bg-gray-200">
              <tr>
                <th className="p-3 border-b">Name</th>
                <th className="p-3 border-b">Current Position</th>
                <th className="p-3 border-b">Experience</th>
                <th className="p-3 border-b">Skills</th>
                <th className="p-3 border-b">Score</th>
                <th className="p-3 border-b">Action</th>
              </tr>
            </thead>
            <tbody>
              {results.map((cv) => (
                <tr key={cv._id} className="border-t">
                  <td className="p-3">{cv.name}</td>
                  <td className="p-3">{cv.current_position}</td>
                  <td className="p-3">{cv.total_experience_years || 0} yrs</td>
                  <td className="p-3 space-x-1">
                    {cv.skills?.slice(0, 4).map((s, i) => (
                      <span
                        key={i}
                        className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs inline-block"
                      >
                        {s}
                      </span>
                    ))}
                  </td>
                  <td className="p-3">{cv.match_score.toFixed(2)}</td>
                  <td className="p-3">
                    <button
                      onClick={() => openSlider(cv)}
                      className="text-blue-600 hover:underline"
                    >
                      View CV
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Slide-over panel */}
      {sliderOpen && (
        <CVSlider
          cvList={results as CVType[]}
          initialIndex={sliderIndex}
          onClose={() => setSliderOpen(false)}
        />
      )}
    </div>
  );
}
