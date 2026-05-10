export default function Loading() {
  return (
    <main className="flex min-h-dvh items-center justify-center" aria-busy="true" aria-live="polite">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-zinc-200 border-t-zinc-700" />
    </main>
  );
}
