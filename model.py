from PIL import Image
import torch
import torchvision.transforms as T
from torchvision import models
import numpy as np

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if DEVICE=='cpu':
  print('NO CUDA SYSTEM!!!')
  
def decode_segmap(image, nc=21):
  label_colors = np.array([(0, 0, 0),  # 0=background
               # 1=aeroplane, 2=bicycle, 3=bird, 4=boat, 5=bottle
               (128, 1, 1), (1, 128 ,1), (128, 128, 1), (1, 1, 128), (128, 1, 128),
               # 6=bus, 7=car, 8=cat, 9=chair, 10=cow
               (1, 128, 128), (128, 128, 128), (64, 1, 1), (192, 1, 1), (64, 128, 1),
               # 11=dining table, 12=dog, 13=horse, 14=motorbike, 15=person
               (192, 128, 1), (64, 1, 128), (192, 1, 128), (64, 128, 128), (192, 128, 128),
               # 16=potted plant, 17=sheep, 18=sofa, 19=train, 20=tv/monitor
               (1, 64, 1), (128, 64, 1), (1, 192, 1), (128, 192, 1), (1, 64, 128)])

  r = np.zeros_like(image).astype(np.uint8)
  g = np.zeros_like(image).astype(np.uint8)
  b = np.zeros_like(image).astype(np.uint8)
  
  for l in range(0, nc):
    idx = image == l
    r[idx] = label_colors[l, 0]
    g[idx] = label_colors[l, 1]
    b[idx] = label_colors[l, 2]
    
  rgb = np.stack([r, g, b], axis=2)
  return rgb

def segment(net, src_filename, dest_filename, dev='cpu'):
    resize_val = 100
    with Image.open(src_filename) as img:
        trf = T.Compose([T.Resize(resize_val), 
                       T.ToTensor(), 
                       T.Normalize(mean = [0.485, 0.456, 0.406], 
                                   std = [0.229, 0.224, 0.225])])
        inp = trf(img).unsqueeze(0).to(dev)
        out = net.to(dev)(inp)['out']
        om = torch.argmax(out.squeeze(), dim=0).detach().cpu().numpy()
        rgb = decode_segmap(om)

        if dest_filename:
          src_resized_img = T.Resize(resize_val)(img)
          src_img = np.array(src_resized_img)
          mask_idx = np.nonzero(rgb)

          cust_img = np.zeros_like(src_img)
          cust_img[::] = [255, 255, 255 ]
          cust_img[mask_idx] = rgb[mask_idx]

          img1 = Image.fromarray(src_img)
          img2 = Image.fromarray(cust_img)

          im = Image.blend(img1, img2, 0.4)  
          im.save(dest_filename)
      
def segmentation(src_filename, dest_filename):
  with torch.no_grad():
	  fcn = models.segmentation.deeplabv3_resnet101(pretrained=True).eval()
	  segment(fcn, src_filename, dest_filename, dev=DEVICE)