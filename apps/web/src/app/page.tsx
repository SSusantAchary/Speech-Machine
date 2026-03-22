"use client";

import { useEffect, useMemo, useRef, useState, type MouseEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api";
import { useRequireAuth } from "@/lib/hooks/useRequireAuth";
import { useTranscriptionModel } from "@/lib/hooks/useTranscriptionModel";
import { createSession, deleteSession, getVideoDurationMs, triggerTranscription, uploadVideoFile } from "@/lib/session";
import { Input } from "@/components/ui/input";
import { AudioTranscriptionPanel } from "@/components/audio-transcription-panel";

type SessionItem = {
  id: number;
  title?: string;
  mode?: string;
  duration_ms: number;
  wpm_avg: number;
  filler_count: number;
  eye_contact_pct: number;
  created_at: string;
  transcription_status: string;
  score?: { total?: number };
};

export default function DashboardPage() {
  useRequireAuth();
  const router = useRouter();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const transcriptionModel = useTranscriptionModel();

  useEffect(() => {
    const load = async () => {
      try {
        const data = await apiFetch<SessionItem[]>("/sessions");
        setSessions(data);
      } catch (_error) {
        setSessions([]);
      }
    };
    load();
  }, []);

  const trend = useMemo(
    () =>
      sessions
        .slice(0, 7)
        .reverse()
        .map((session) => ({
          date: new Date(session.created_at).toLocaleDateString(),
          score: session.score?.total ?? 0,
        })),
    [sessions]
  );

  const bestScore = Math.max(0, ...sessions.map((s) => s.score?.total ?? 0));

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError("Choose a video file first.");
      return;
    }
    if (transcriptionModel.selectedAudioBackendStatus?.supported && !transcriptionModel.selectedAudioModelOption?.available) {
      setUploadError("Download the selected transcription model before transcribing this video.");
      return;
    }

    setUploading(true);
    setUploadError(null);
    try {
      const durationMs = await getVideoDurationMs(selectedFile);
      const session = await createSession({
        title: selectedFile.name.replace(/\.[^.]+$/, ""),
        mode: "Upload",
        prompt: `Uploaded video: ${selectedFile.name}`,
        goal: "Transcribe uploaded video",
        durationMs,
        wpmAvg: 0,
        fillerCount: 0,
        eyeContactPct: 0,
        transcript: [],
        metrics: [],
        tags: ["uploaded"],
      });
      await uploadVideoFile(session.id, selectedFile);
      await triggerTranscription(session.id, transcriptionModel.effectiveSelection);
      router.push(`/session/${session.id}`);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteSession = async (event: MouseEvent<HTMLButtonElement>, sessionId: number) => {
    event.preventDefault();
    event.stopPropagation();
    if (!window.confirm("Delete this session and all of its saved data?")) {
      return;
    }

    setDeletingSessionId(sessionId);
    try {
      await deleteSession(sessionId);
      setSessions((current) => current.filter((session) => session.id !== sessionId));
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Unable to delete session.");
    } finally {
      setDeletingSessionId(null);
    }
  };

  return (
    <div className="min-h-screen px-6 py-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-10">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-ink/60">Speech-Machine</p>
            <h1 className="font-display text-4xl font-semibold">Your practice dashboard</h1>
            <p className="text-sm text-ink/70">Track streaks, score peaks, and your speaking rhythm.</p>
          </div>
          <Link href="/record">
            <Button size="lg" className="rounded-full">
              Start session
            </Button>
          </Link>
        </header>

        <section className="grid gap-6 md:grid-cols-4">
          <Card>
            <CardHeader>
              <CardTitle>Best score</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{bestScore}</p>
              <p className="text-xs text-ink/60">Personal record</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Sessions</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{sessions.length}</p>
              <p className="text-xs text-ink/60">Total saved</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Weekly trend</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={80}>
                <LineChart data={trend}>
                  <XAxis dataKey="date" hide />
                  <YAxis hide />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" stroke="#232732" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Streak</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{Math.min(7, sessions.length)} days</p>
              <p className="text-xs text-ink/60">Keep the rhythm</p>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 md:grid-cols-[1.4fr_1fr]">
          <Card className="bg-white/80">
            <CardHeader>
              <CardTitle>Recent sessions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {sessions.slice(0, 6).map((session) => (
                  <div
                    key={session.id}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-ink/5 bg-white/60 px-4 py-3 transition hover:bg-white"
                  >
                    <Link href={`/session/${session.id}`} className="min-w-0 flex-1">
                      <div>
                        <p className="text-sm font-semibold">{session.title || session.mode || "Session"}</p>
                        <p className="text-xs text-ink/60">
                          {new Date(session.created_at).toLocaleString()} - {Math.round(session.duration_ms / 1000)}s
                        </p>
                      </div>
                    </Link>
                    <div className="flex items-center gap-3">
                      <Badge>{session.score?.total ?? 0}</Badge>
                      <span className="text-xs text-ink/60">WPM {Math.round(session.wpm_avg)}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        aria-label={`Delete session ${session.title || session.mode || session.id}`}
                        disabled={deletingSessionId === session.id}
                        onClick={(event) => handleDeleteSession(event, session.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
                {sessions.length === 0 && (
                  <p className="text-sm text-ink/60">No sessions yet. Start your first session.</p>
                )}
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white/80">
            <CardHeader>
              <CardTitle>Upload Video</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 text-sm text-ink/70">
                <p>Upload an existing recording to generate a transcript and review it like a normal session.</p>
                <Input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
                />
                <div className="rounded-2xl bg-white/70 p-3">
                  <p className="text-sm font-semibold text-ink">{selectedFile?.name || "No file selected"}</p>
                  {selectedFile && (
                    <p className="text-xs text-ink/60">
                      {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
                    </p>
                  )}
                </div>
                <AudioTranscriptionPanel
                  transcriptionModel={transcriptionModel}
                  helperText="The selected backend and model are used when transcribing uploaded videos."
                />
                <Button className="w-full" onClick={handleUpload} disabled={uploading}>
                  {uploading ? "Uploading..." : "Upload and transcribe"}
                </Button>
                {uploadError && <p className="text-sm text-red-600">{uploadError}</p>}
                {transcriptionModel.error && <p className="text-sm text-red-600">{transcriptionModel.error}</p>}
                <div className="text-xs text-ink/60">
                  Supported formats follow your browser upload support, typically `.mp4`, `.mov`, and `.webm`.
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </div>
  );
}
