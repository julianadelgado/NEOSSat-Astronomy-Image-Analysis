import warnings
warnings.filterwarnings("ignore")

import torch
from collections import OrderedDict
import glob
import os
import numpy as np
from astropy.io import fits
from PIL import Image

def load_image(filepath):
    """Load and normalize image from FITS or common formats."""
    # Read FITS
    if filepath.lower().endswith(('.fits', '.fit')):
        with fits.open(filepath) as hdul:
            data = hdul[0].data
            if data is None and len(hdul) > 1:
                data = hdul[1].data
            data = np.array(data, dtype=np.float32)
    else:
        # Png/Jpg
        img = Image.open(filepath).convert('L')
        data = np.array(img, dtype=np.float32)
        
    # Replace NaN with 0
    data = np.nan_to_num(data)
    
    # Z-score normalization
    data_mean = np.mean(data)
    data_std = np.std(data)
    if data_std > 0:
        data = (data - data_mean) / data_std
    else:
        data = data - data_mean
        
    # Ensure divisible by 4 for the model's 2 down-sampling layers
    h, w = data.shape
    pad_h = (4 - (h % 4)) % 4
    pad_w = (4 - (w % 4)) % 4
    if pad_h > 0 or pad_w > 0:
        data = np.pad(data, ((0, pad_h), (0, pad_w)), mode='reflect')
        
    return data, h, w, pad_h, pad_w

def run_inference(batch_size=1):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    model_path = os.path.join(os.path.dirname(__file__), 'Att_Coasmic_CoNN.pth')
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        return
        
    print(f"Loading model from {model_path}...")
    try:
        state_dict = torch.load(model_path, map_location=device, weights_only=False)
    except TypeError:
        # Fallback for older torch versions
        state_dict = torch.load(model_path, map_location=device)

    
    # Remove 'module.' prefix if it exists
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = k.replace('module.', '')
        new_state_dict[name] = v
        
    from unet_model import UNet_module
    model = UNet_module(
        n_channels=1,
        n_classes=1,
        hidden=32,
        norm='group',
        norm_setting=[8, 0, True],
        conv_type='unet',
        down_type='maxpool',
        up_type='transconv',
        att=True,
        deeper=True
    )
    model.to(device)
    
    print("Model loaded successfully.")

    # Find images
    dataset_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    images = glob.glob(os.path.join(dataset_dir, '**', '*.fits'), recursive=True)
    if not images:
        images = glob.glob(os.path.join(dataset_dir, '**', '*.png'), recursive=True)
        
    if not images:
        print("No images found in dataset folder.")
        return
        
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)
    results_file = os.path.join(output_dir, 'cosmic_ray_hits.txt')
    
    hits = []
    
    with torch.no_grad():
        model.eval()
        for i in range(0, len(images), batch_size):
            batch_paths = images[i:i+batch_size]
            batch_data = []
            meta_info = []

            print(f"\nProcessing batch {i//batch_size + 1}/{(len(images) + batch_size - 1)//batch_size} ({len(batch_paths)} images)...")

            for img_path in batch_paths:
                img_data, orig_h, orig_w, pad_h, pad_w = load_image(img_path)
                batch_data.append(img_data)
                meta_info.append((img_path, orig_h, orig_w))

            # Pad to max in batch to allow varying sizes
            max_h = max(d.shape[0] for d in batch_data)
            max_w = max(d.shape[1] for d in batch_data)
            
            stacked_data = []
            for d in batch_data:
                h, w = d.shape
                p_h = max_h - h
                p_w = max_w - w
                if p_h > 0 or p_w > 0:
                    d = np.pad(d, ((0, p_h), (0, p_w)), mode='reflect')
                stacked_data.append(d)

            input_tensor = torch.from_numpy(np.array(stacked_data)).unsqueeze(1).to(device)
            
            output = model(input_tensor)
            
            # Squeeze channel dim only: shape (B, 1, H, W) -> (B, H, W)
            out_imgs = output.squeeze(1).cpu().numpy()
            
            for b_idx, (img_path, orig_h, orig_w) in enumerate(meta_info):
                # Remove padding back to original image size
                out_img = out_imgs[b_idx][:orig_h, :orig_w]
                
                # Check if there is a cosmic ray hit reported (e.g. threshold > 0.5)
                has_hit = np.any(out_img > 0.5)
                if has_hit:
                    hits.append(os.path.basename(img_path))
                    print(f"[{os.path.basename(img_path)}] Cosmic ray detected!")
                    
                    # Format output to viewable image (0-255 uint8)
                    mask = (out_img > 0.5).astype(np.uint8) * 255
                    output_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(img_path))[0]}_mask.png")
                    
                    Image.fromarray(mask).save(output_path)
                else:
                    print(f"[{os.path.basename(img_path)}] No cosmic rays detected. Skipping mask generation.")

    # Write hits to txt file
    with open(results_file, 'w') as f:
        if hits:
            f.write("Images containing cosmic rays:\n\n")
            f.write("\n".join(hits))
        else:
            f.write("No images contained cosmic rays.\n")
            
    print(f"\nInference complete. Results saved to {results_file}")

if __name__ == "__main__":
    run_inference()

