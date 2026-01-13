"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useState, Suspense, useEffect, useRef } from "react";

const API_URL = "http://localhost:8000";

interface Outputs {
  isolated: string;
  without_isolated: string;
  isolated_mp3: string;
  without_isolated_mp3: string;
}

function getUserId(): string {
  const match = document.cookie.match(/user_id=([^;]+)/);
  if (match) return match[1];
  const id = crypto.randomUUID();
  document.cookie = `user_id=${id}; path=/; max-age=31536000`;
  return id;
}

interface LibraryOutput {
  id: string;
  prompt: string;
  created_at: string;
}

interface LibraryUpload {
  id: string;
  filename: string;
  created_at: string;
  duration_seconds?: number;
  outputs: LibraryOutput[];
}

function UploadPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const uploadId = searchParams.get("upload_id");
  const outputId = searchParams.get("output_id");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({ completed: 0, total: 0 });
  const [prompt, setPrompt] = useState("");
  const [submittedPrompt, setSubmittedPrompt] = useState("");
  const [processing, setProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState({ completed: 0, total: 0 });
  const [outputs, setOutputs] = useState<Outputs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [library, setLibrary] = useState<LibraryUpload[]>([]);
  const [uploadFilename, setUploadFilename] = useState<string>("");
  const [lastPrompt, setLastPrompt] = useState<string>("");
  const [currentUploadId, setCurrentUploadId] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getUserId();
    fetchLibrary();
  }, []);

  useEffect(() => {
    if (uploadId) {
      // Clear outputs when navigating to a different upload
      setOutputs(null);
      setLastPrompt("");
      fetchUploadInfo();
    }
  }, [uploadId]);

  useEffect(() => {
    if (outputId) {
      // Clear and refetch when navigating to a different output
      setOutputs(null);
      setLastPrompt("");
      fetchOutputData();
    }
  }, [outputId]);

  const fetchLibrary = async () => {
    try {
      const res = await fetch(`${API_URL}/library`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setLibrary(data.uploads || []);
      }
    } catch (e) {
      console.error("Failed to fetch library", e);
    }
  };

  const fetchUploadInfo = async () => {
    try {
      const res = await fetch(`${API_URL}/status/upload/${uploadId}`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setUploadFilename(data.filename || "");
        setLastPrompt(data.last_prompt || "");
        setCurrentUploadId(uploadId || "");
      }
    } catch (e) {
      console.error("Failed to fetch upload info", e);
    }
  };

  const fetchOutputData = async () => {
    if (!outputId) return;
    try {
      const res = await fetch(`${API_URL}/status/output/${outputId}`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "complete" && data.outputs) {
          setOutputs(data.outputs);
          setLastPrompt(data.prompt || "");
        }
        // Fetch upload info for filename
        if (data.upload_id) {
          setCurrentUploadId(data.upload_id);
          const uploadRes = await fetch(`${API_URL}/status/upload/${data.upload_id}`, {
            credentials: "include",
          });
          if (uploadRes.ok) {
            const uploadData = await uploadRes.json();
            setUploadFilename(uploadData.filename || "");
          }
        }
      }
    } catch (e) {
      console.error("Failed to fetch output data", e);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_URL}/upload`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });
    
    if (!res.ok) {
      const err = await res.json();
      setError(err.detail || "Upload failed");
      setUploading(false);
      return;
    }
    
    const { upload_id } = await res.json();

    const poll = async () => {
      const statusRes = await fetch(`${API_URL}/status/upload/${upload_id}`, {
        credentials: "include",
      });
      const status = await statusRes.json();
      
      // Update progress
      if (status.chunks && status.completed_chunks !== undefined) {
        setUploadProgress({ completed: status.completed_chunks, total: status.chunks });
      }
      
      if (status.status === "complete") {
        setUploading(false);
        setUploadProgress({ completed: 0, total: 0 });
        fetchLibrary(); // Refresh library after upload completes
        router.push(`/?upload_id=${upload_id}`);
      } else if (status.status === "failed") {
        setError("Upload failed");
        setUploading(false);
        setUploadProgress({ completed: 0, total: 0 });
      } else {
        setTimeout(poll, 1000);
      }
    };
    poll();
  };

  const handlePromptSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || !uploadId) return;

    setProcessing(true);
    setError(null);
    setOutputs(null);
    setSubmittedPrompt(prompt);
    
    const res = await fetch(`${API_URL}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ upload_id: uploadId, prompt }),
      credentials: "include",
    });
    
    if (!res.ok) {
      const err = await res.json();
      setError(err.detail || "Processing failed");
      setProcessing(false);
      return;
    }
    
    const { output_id } = await res.json();

    const poll = async () => {
      const statusRes = await fetch(`${API_URL}/status/output/${output_id}`, {
        credentials: "include",
      });
      const status = await statusRes.json();
      
      // Update progress
      if (status.chunks && status.completed_chunks !== undefined) {
        setProcessingProgress({ completed: status.completed_chunks, total: status.chunks });
      }
      
      if (status.status === "complete") {
        setOutputs(status.outputs);
        setProcessing(false);
        setProcessingProgress({ completed: 0, total: 0 });
        setLastPrompt(status.prompt || submittedPrompt);
        setPrompt("");
        fetchLibrary(); // Refresh library after processing completes
      } else if (status.status === "failed") {
        setError("Processing failed");
        setProcessing(false);
        setProcessingProgress({ completed: 0, total: 0 });
      } else {
        setTimeout(poll, 1000);
      }
    };
    poll();
  };

  const handleDownload = async (url: string, name: string) => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error("Download failed:", error);
    }
  };

  const handleNewPrompt = () => {
    setOutputs(null);
    setPrompt("");
    setLastPrompt("");
    if (currentUploadId) {
      router.push(`/?upload_id=${currentUploadId}`);
    }
  };

  const handleNewUpload = () => {
    setOutputs(null);
    setPrompt("");
    setLastPrompt("");
    setUploadFilename("");
    router.push("/");
  };

  // State 3: Has processed outputs (2 audio files)
  if (outputs && (uploadId || outputId)) {
    const isolatedUrl = `${API_URL}${outputs.isolated}`;
    const withoutIsolatedUrl = `${API_URL}${outputs.without_isolated}`;
    const isolatedMp3Url = `${API_URL}${outputs.isolated_mp3}`;
    const withoutIsolatedMp3Url = `${API_URL}${outputs.without_isolated_mp3}`;
    
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
        <button 
          onClick={handleNewUpload} 
          className="fixed top-8 left-8 text-base text-gray-600 hover:text-black font-medium flex items-center gap-2"
        >
          <span className="text-xl">←</span> New Upload
        </button>
        
        <div className="flex flex-col items-center gap-2">
          {uploadFilename && (
            <h2 className="text-3xl font-bold uppercase tracking-wide" style={{ fontFamily: 'Helvetica Neue, sans-serif' }}>
              {uploadFilename}
            </h2>
          )}
        </div>
        
        <div className="flex flex-col gap-6 w-full max-w-2xl">
          {/* <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-base font-medium text-gray-700 uppercase tracking-wide">Combined</p>
              <div className="flex gap-3">
                <button 
                  onClick={() => handleDownload(combinedUrl, "combined.wav")} 
                  className="text-sm text-gray-600 hover:text-black font-medium"
                >
                  WAV
                </button>
                <button 
                  onClick={() => handleDownload(combinedMp3Url, "combined.mp3")} 
                  className="text-sm text-gray-600 hover:text-black font-medium"
                >
                  MP3
                </button>
              </div>
            </div>
            <audio controls src={combinedUrl} className="w-full h-14" />
          </div> */}
          
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-base font-medium text-gray-700 uppercase tracking-wide">Isolated - "{lastPrompt}"</p>
              <div className="flex gap-3">
                <button 
                  onClick={() => handleDownload(isolatedUrl, "isolated.wav")} 
                  className="text-sm text-gray-600 hover:text-black font-medium"
                >
                  WAV
                </button>
                <button 
                  onClick={() => handleDownload(isolatedMp3Url, "isolated.mp3")} 
                  className="text-sm text-gray-600 hover:text-black font-medium"
                >
                  MP3
                </button>
              </div>
            </div>
            <audio controls src={isolatedUrl} className="w-full h-14" />
          </div>
          
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-base font-medium text-gray-700 uppercase tracking-wide">Without Isolated</p>
              <div className="flex gap-3">
                <button 
                  onClick={() => handleDownload(withoutIsolatedUrl, "without_isolated.wav")} 
                  className="text-sm text-gray-600 hover:text-black font-medium"
                >
                  WAV
                </button>
                <button 
                  onClick={() => handleDownload(withoutIsolatedMp3Url, "without_isolated.mp3")} 
                  className="text-sm text-gray-600 hover:text-black font-medium"
                >
                  MP3
                </button>
              </div>
            </div>
            <audio controls src={withoutIsolatedUrl} className="w-full h-14" />
          </div>
        </div>
        
        <div className="flex gap-4 mt-4">
          <button 
            onClick={handleNewPrompt} 
            className="bg-black text-white rounded-lg px-8 py-4 text-base font-medium hover:bg-gray-800"
          >
            New Prompt
          </button>
        </div>
        
        {error && <p className="text-red-500 text-base font-medium">{error}</p>}
      </div>
    );
  }

  // State 2: Uploaded, ready to prompt (no outputs yet)
  if (uploadId) {
    const uploadUrl = `${API_URL}/uploads/${uploadId}.mp3`;
    
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
        <button 
          onClick={handleNewUpload} 
          className="fixed top-8 left-8 text-base text-gray-600 hover:text-black font-medium flex items-center gap-2 cursor-pointer"
        >
          <span className="text-xl">←</span> New Upload
        </button>
        
        {uploadFilename && (
          <h2 className="text-3xl font-bold uppercase tracking-wide" style={{ fontFamily: 'Helvetica Neue, sans-serif' }}>
            {uploadFilename}
          </h2>
        )}
        
        <div className="w-full max-w-2xl mb-4">
          <audio controls src={uploadUrl} className="w-full h-14" />
        </div>
        
        {!processing && <p className="text-gray-600 text-lg font-medium uppercase tracking-wide">Describe what you want to isolate.</p>}
        
        <form onSubmit={handlePromptSubmit} className="flex flex-col gap-5 w-full max-w-2xl">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="piano and bass"
            disabled={processing}
            className="border-2 border-gray-300 rounded-lg px-6 py-5 w-full h-40 resize-none text-lg focus:border-gray-500 focus:outline-none"
          />
          <button 
            type="submit" 
            disabled={processing} 
            className="bg-black text-white rounded-lg px-8 py-5 text-lg font-medium disabled:opacity-50 hover:bg-gray-800"
          >
            {processing ? `Isolating "${submittedPrompt}" sounds...` : "Submit"}
          </button>
          
          {processing && processingProgress.total > 0 && (
            <div className="flex flex-col gap-2">
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-black h-full transition-all duration-300 ease-out"
                  style={{ width: `${(processingProgress.completed / processingProgress.total) * 100}%` }}
                />
              </div>
              <p className="text-sm text-gray-600 font-medium text-center">
                {processingProgress.completed} / {processingProgress.total} chunks processed
              </p>
            </div>
          )}
        </form>
        
        {error && <p className="text-red-500 text-base font-medium">{error}</p>}
      </div>
    );
  }

  // State 1: No upload yet
  return (
    <div className="flex min-h-screen flex-col items-center px-8 py-12">
      <div className="flex-1 flex items-center justify-center">
        {uploading ? (
          <div className="flex flex-col items-center gap-4 w-full max-w-md">
            <p className="text-gray-500 text-xl uppercase tracking-wide font-medium">Uploading...</p>
            {uploadProgress.total > 0 && (
              <>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div 
                    className="bg-black h-full transition-all duration-300 ease-out"
                    style={{ width: `${(uploadProgress.completed / uploadProgress.total) * 100}%` }}
                  />
                </div>
                <p className="text-sm text-gray-600 font-medium">
                  {uploadProgress.completed} / {uploadProgress.total} chunks uploaded
                </p>
              </>
            )}
            {error && <p className="text-red-500 text-base font-medium mt-4">{error}</p>}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center min-h-[70vh] gap-8">
            <div className="flex flex-col items-center">
              <h1 className="text-5xl mb-10 w-[900px] text-justify uppercase leading-tight" style={{ fontFamily: 'Helvetica Neue, sans-serif', fontWeight: 700 }}>isolate any part of an audio track with prompts.</h1>
              <h1 className="text-5xl mb-10 w-[900px] text-justify uppercase leading-tight" style={{ fontFamily: 'Helvetica Neue, sans-serif', fontWeight: 700 }}>EX: "synthesizer only", "drums and bass", "vocals only"</h1>
              <h1 className="text-5xl mb-10 w-[900px] text-justify uppercase leading-tight" style={{ fontFamily: 'Helvetica Neue, sans-serif', fontWeight: 700 }}>its entirely free, so try it (.mp3, .wav, .m4a)</h1>
                
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="py-6 px-12 rounded-lg text-2xl bg-black text-white border-2 border-black cursor-pointer uppercase hover:bg-gray-800 transition-colors"
                style={{ fontFamily: 'Helvetica Neue, sans-serif', fontWeight: 700 }}
              >
                Choose File
              </button>
            </div>
            {error && <p className="text-red-500 text-base font-medium">{error}</p>}
            <input 
              ref={fileInputRef}
              type="file" 
              accept=".mp3,.wav,.m4a,audio/mpeg,audio/wav,audio/mp4,audio/x-m4a" 
              onChange={handleUpload}
              className="hidden"
            />
          </div>
        )}
      </div>

      {!uploading && library.length > 0 && (
        <div className="w-[900px] pb-12">
          <div className="w-full mb-8 border-t border-gray-300" />
          
          <h2 className="text-xl uppercase tracking-wide mb-8 text-center text-gray-600" style={{ fontFamily: 'Helvetica Neue, sans-serif', fontWeight: 500 }}>
            uploads
          </h2>
          <div className="flex flex-col">
            {library.map((upload, index) => (
              <div key={upload.id}>
                <button
                  onClick={() => router.push(`/?upload_id=${upload.id}`)}
                  className="w-full py-4 text-left hover:text-gray-600 transition-colors cursor-pointer flex justify-between items-start"
                >
                  <div className="flex flex-col gap-1">
                    <p className="text-lg uppercase" style={{ fontFamily: 'Helvetica Neue, sans-serif', fontWeight: 600 }}>
                      {upload.filename}
                    </p>
                  </div>
                  {upload.duration_seconds && (
                    <p className="text-sm text-gray-500 flex-shrink-0">
                      {Math.floor(upload.duration_seconds / 60)}:{String(Math.floor(upload.duration_seconds % 60)).padStart(2, '0')}
                    </p>
                  )}
                </button>
                
                {upload.outputs.length > 0 && (
                  <div className="ml-1 flex flex-col -mt-2">
                    {upload.outputs.map((output) => (
                      <button
                        key={output.id}
                        onClick={() => router.push(`/?output_id=${output.id}`)}
                        className="w-full py-1.5 text-left hover:text-gray-600 transition-colors cursor-pointer"
                      >
                        <p className="text-md text-gray-500 lowercase italic">
                          ↳ {output.prompt}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
                
                {index < library.length - 1 && (
                  <div className="border-t border-gray-200" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-gray-500 text-sm">Loading...</div>}>
      <UploadPage />
    </Suspense>
  );
}
