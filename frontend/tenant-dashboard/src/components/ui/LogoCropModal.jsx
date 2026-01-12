/**
 * LogoCropModal - Image cropping modal for logo uploads
 *
 * Features:
 * - Circular or rectangular crop area
 * - Zoom and pan controls
 * - Generates cropped image blob for upload
 *
 * Usage:
 *   <LogoCropModal
 *     isOpen={showCropModal}
 *     onClose={() => setShowCropModal(false)}
 *     imageSrc={selectedImageUrl}
 *     onCropComplete={(croppedBlob) => handleUpload(croppedBlob)}
 *     cropShape="round" // 'round' or 'rect'
 *     aspectRatio={1} // 1 for square, 16/9 for landscape, etc.
 *   />
 */

import { useState, useCallback } from 'react';
import Cropper from 'react-easy-crop';
import { XMarkIcon, MagnifyingGlassPlusIcon, MagnifyingGlassMinusIcon } from '@heroicons/react/24/outline';

// Helper function to create cropped image
async function getCroppedImg(imageSrc, pixelCrop, circular = false) {
  const image = await createImage(imageSrc);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  if (!ctx) {
    throw new Error('Could not get canvas context');
  }

  // Set canvas size to the cropped area
  canvas.width = pixelCrop.width;
  canvas.height = pixelCrop.height;

  // Draw cropped image
  ctx.drawImage(
    image,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    pixelCrop.width,
    pixelCrop.height
  );

  // If circular crop, apply circular mask
  if (circular) {
    ctx.globalCompositeOperation = 'destination-in';
    ctx.beginPath();
    ctx.arc(
      pixelCrop.width / 2,
      pixelCrop.height / 2,
      pixelCrop.width / 2,
      0,
      Math.PI * 2
    );
    ctx.closePath();
    ctx.fill();
  }

  // Return as blob
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error('Canvas to Blob failed'));
        }
      },
      'image/png',
      1
    );
  });
}

// Helper to load image
function createImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener('load', () => resolve(image));
    image.addEventListener('error', (error) => reject(error));
    image.crossOrigin = 'anonymous';
    image.src = url;
  });
}

export default function LogoCropModal({
  isOpen,
  onClose,
  imageSrc,
  onCropComplete,
  cropShape = 'round',
  aspectRatio = 1,
  title = 'Crop Image',
}) {
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState(null);
  const [loading, setLoading] = useState(false);

  const onCropChange = useCallback((crop) => {
    setCrop(crop);
  }, []);

  const onZoomChange = useCallback((zoom) => {
    setZoom(zoom);
  }, []);

  const onCropAreaComplete = useCallback((croppedArea, croppedAreaPixels) => {
    setCroppedAreaPixels(croppedAreaPixels);
  }, []);

  const handleConfirm = async () => {
    if (!croppedAreaPixels) return;

    setLoading(true);
    try {
      const croppedBlob = await getCroppedImg(
        imageSrc,
        croppedAreaPixels,
        cropShape === 'round'
      );
      onCropComplete(croppedBlob);
      onClose();
    } catch (error) {
      console.error('Error cropping image:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setCrop({ x: 0, y: 0 });
    setZoom(1);
    onClose();
  };

  if (!isOpen || !imageSrc) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center animate-backdrop">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleCancel}
      />

      {/* Modal */}
      <div className="relative bg-theme-surface rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-theme">
          <h3 className="text-lg font-semibold text-theme">{title}</h3>
          <button
            onClick={handleCancel}
            className="p-1.5 rounded-lg hover:bg-theme-border-light text-theme-muted hover:text-theme transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Cropper Area */}
        <div className="relative h-80 bg-theme-background">
          <Cropper
            image={imageSrc}
            crop={crop}
            zoom={zoom}
            aspect={aspectRatio}
            cropShape={cropShape}
            showGrid={cropShape === 'rect'}
            onCropChange={onCropChange}
            onZoomChange={onZoomChange}
            onCropComplete={onCropAreaComplete}
          />
        </div>

        {/* Zoom Controls */}
        <div className="px-6 py-4 bg-theme-surface-elevated border-t border-theme">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setZoom((z) => Math.max(1, z - 0.1))}
              className="p-2 rounded-lg hover:bg-theme-border-light text-theme-muted hover:text-theme transition-colors"
              disabled={zoom <= 1}
            >
              <MagnifyingGlassMinusIcon className="w-5 h-5" />
            </button>

            <input
              type="range"
              min={1}
              max={3}
              step={0.1}
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
              className="flex-1 h-2 bg-theme-border rounded-lg appearance-none cursor-pointer accent-theme-primary"
            />

            <button
              onClick={() => setZoom((z) => Math.min(3, z + 0.1))}
              className="p-2 rounded-lg hover:bg-theme-border-light text-theme-muted hover:text-theme transition-colors"
              disabled={zoom >= 3}
            >
              <MagnifyingGlassPlusIcon className="w-5 h-5" />
            </button>
          </div>

          <p className="text-xs text-theme-muted text-center mt-2">
            Drag to reposition, scroll or use slider to zoom
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-theme">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm font-medium text-theme-secondary hover:bg-theme-border-light rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-theme-primary hover:bg-theme-primary-dark rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Processing...
              </>
            ) : (
              'Confirm & Upload'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
