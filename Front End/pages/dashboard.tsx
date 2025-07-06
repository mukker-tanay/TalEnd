import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import CVSlider, { CVType } from "../components/CVSlider";

type UploadedCV = {
  _id: string;
  original_filename: string;
  stored_filename: string;
  uploaded_at: string;
  processing_status: string;
};

export default function Dashboard() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [cvList, setCvList] = useState<UploadedCV[]>([]);
  const [message, setMessage] = useState("");
  const [selectedCV, setSelectedCV] = useState<UploadedCV | null>(null);
  const [sliderOpen, setSliderOpen] = useState(false);
  const [sliderIndex, setSliderIndex] = useState(0);
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  useEffect(() => {
    if (!token) router.push("/login");
    else fetchCVs();
  }, []);

  const fetchCVs = async () => {
    try {
      const res = await fetch("http://localhost:8000/list-cvs", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (Array.isArray(data)) {
        setCvList(data);
      } else {
        setCvList([]);
      }
    } catch (error) {
      console.error("Failed to fetch CVs", error);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/upload-cv", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      setMessage("✅ Upload successful!");
      setFile(null);
      fetchCVs();
    } catch (err: any) {
      console.error(err);
      setMessage("❌ Upload failed.");
    }
  };

  const closePanel = () => {
    setSelectedCV(null);
  };

  const openSlider = (cv: UploadedCV) => {
    const idx = cvList.findIndex((item) => item._id === cv._id);
    setSliderIndex(idx);
    setSliderOpen(true);
  };

  return (
    <>
      <div className="min-h-screen w-full bg-gray-50">
        <div className="max-w-4xl mx-auto p-8">
          <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

          <form onSubmit={handleUpload} className="bg-white p-6 rounded shadow-md mb-8 max-w-lg">
            <label className="block mb-2 font-medium">Upload CV</label>
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              className="mb-4"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              required
            />
            <button
              type="submit"
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Upload
            </button>
            {message && <p className="mt-4 text-sm">{message}</p>}
          </form>

          <h2 className="text-xl font-semibold mb-2">Uploaded CVs</h2>
          <div className="bg-white shadow-md rounded overflow-x-auto max-w-3xl">
            <table className="w-full text-sm text-left border-collapse">
              <thead className="bg-gray-200">
                <tr>
                  <th className="p-3 border-b">File Name</th>
                  <th className="p-3 border-b">Status</th>
                  <th className="p-3 border-b">Uploaded</th>
                  <th className="p-3 border-b">Action</th>
                </tr>
              </thead>
              <tbody>
                {cvList.map((cv) => (
                  <tr key={cv._id} className="border-t">
                    <td className="p-3">{cv.original_filename}</td>
                    <td className="p-3">{cv.processing_status}</td>
                    <td className="p-3">{new Date(cv.uploaded_at).toLocaleString()}</td>
                    <td className="p-3">
                      <button
                        onClick={() => openSlider(cv)}
                        className="text-blue-600 hover:underline"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
                {cvList.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-4 text-center text-gray-500">
                      No CVs uploaded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      {/* Slide-over overlay */}
      {sliderOpen && (
        <CVSlider
          cvList={cvList as CVType[]}
          initialIndex={sliderIndex}
          onClose={() => setSliderOpen(false)}
        />
      )}
    </>
  );
}
