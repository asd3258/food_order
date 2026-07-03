/**
 * Compresses an image to a WebP data URL with a maximum width/height.
 * Helps save bandwidth and storage space when uploading to MinIO.
 */
export function compressImage(file: File, maxWidth = 1920, maxHeight = 1920, quality = 0.8): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const img = new Image()
      img.onload = () => {
        let width = img.width
        let height = img.height

        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height)
          width = width * ratio
          height = height * ratio
        }

        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height

        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('Failed to get canvas context'))
          return
        }

        ctx.drawImage(img, 0, 0, width, height)

        // WebP is widely supported in modern browsers and provides better compression.
        // However, if the browser (e.g. older iOS Safari) doesn't support WebP export,
        // it will fall back to uncompressed PNG, which makes the file size huge.
        let dataUrl = canvas.toDataURL('image/webp', quality)
        if (dataUrl.startsWith('data:image/png')) {
          dataUrl = canvas.toDataURL('image/jpeg', quality)
        }
        resolve(dataUrl)
      }
      img.onerror = () => reject(new Error('Failed to load image'))
      img.src = e.target?.result as string
    }
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.readAsDataURL(file)
  })
}
