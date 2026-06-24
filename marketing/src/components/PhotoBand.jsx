export default function PhotoBand() {
  return (
    <section className="relative">
      <img
        src="/images/networking-event.jpg"
        alt="People talking and connecting at a networking event"
        loading="lazy"
        width="1920"
        height="1080"
        className="w-full h-[44vh] min-h-[320px] max-h-[520px] object-cover"
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(90deg, rgba(13,27,42,0.82) 0%, rgba(13,27,42,0.55) 45%, rgba(13,27,42,0.2) 100%)",
        }}
      />
      <div className="absolute inset-0 flex items-center">
        <div className="container-prose">
          <p className="max-w-xl text-white text-2xl sm:text-4xl font-extrabold leading-[1.1] tracking-tight">
            You spent weeks getting these people in one room.
            <span className="text-wash"> Keep them.</span>
          </p>
        </div>
      </div>
    </section>
  );
}
