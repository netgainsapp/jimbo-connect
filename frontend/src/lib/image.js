// Shrink a picked image to something a profile actually needs before it is sent.
//
// Profile photos are stored as base64 data URLs on the user document. Sending
// the original file was doubly broken: base64 inflates bytes by ~37%, so a
// 1.8MB photo became 2.5M characters and blew the server's 2,200,000 field cap
// with a 422 the user saw as a silent "didn't save"; and a normal phone photo
// is 3 to 8MB, which the old 2MB client check rejected outright. Almost nobody
// could set a picture.
//
// Downscaling here makes both problems disappear: the result is tens of
// kilobytes, so it always fits, uploads fast, and keeps the documents small.

const MAX_EDGE = 512; // rendered at 28-96px; 512 covers retina with room to spare
const QUALITY = 0.85;
// Only a sanity bound so a huge file cannot wedge the decoder. Real photos are
// far under this, and anything that fits gets shrunk regardless.
export const MAX_SOURCE_BYTES = 25 * 1024 * 1024;

export function shrinkImageFile(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      const scale = Math.min(1, MAX_EDGE / Math.max(img.width, img.height));
      const w = Math.max(1, Math.round(img.width * scale));
      const h = Math.max(1, Math.round(img.height * scale));
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      // JPEG has no alpha, so a transparent PNG would composite onto black
      // without this.
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, w, h);
      ctx.drawImage(img, 0, 0, w, h);
      resolve(canvas.toDataURL("image/jpeg", QUALITY));
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      // Chrome cannot decode HEIC, which is what an iPhone hands over by
      // default, so this path is reachable with a perfectly valid photo.
      reject(new Error("That image could not be read. Try a JPG or PNG."));
    };
    img.src = url;
  });
}
