export default function DashboardLoading() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#e8e6e3] flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-2 border-[#c9a050] border-t-transparent rounded-full animate-spin mx-auto mb-6" />
        <p className="text-sm tracking-[0.2em] uppercase text-[#8a8a8a]">Cargando</p>
      </div>
    </div>
  );
}
