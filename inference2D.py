"""
Adapted from the inference.py to demonstate the usage of the util functions.
"""

import sys
import numpy as np
import pydensecrf.densecrf as dcrf
import ipdb

# Get im{read,write} from somewhere.
try:
    from cv2 import imread, imwrite
except ImportError:
    # Note that, sadly, skimage unconditionally import scipy and matplotlib,
    # so you'll need them if you don't have OpenCV. But you probably have them.
    from skimage.io import imread, imsave
    imwrite = imsave
    # TODO: Use scipy instead.

from pydensecrf.utils import unary_from_labels, create_pairwise_bilateral, create_pairwise_gaussian

if len(sys.argv) != 4:
    print("Usage: python {} IMAGE ANNO OUTPUT".format(sys.argv[0]))
    print("")
    print("IMAGE and ANNO are inputs and OUTPUT is where the result should be written.")
    print("If there's at least one single full-black pixel in ANNO, black is assumed to mean unknown.")
    sys.exit(1)

fn_im = sys.argv[1]
fn_anno = sys.argv[2]
fn_output = sys.argv[3]

##################################
### Read images and annotation ###
##################################
img = imread(fn_im)

# Convert the annotation's RGB color to a single 32-bit integer color 0xBBGGRR
anno_rgb = imread(fn_anno,0).astype(np.int32)
ipdb.set_trace()
anno_rgb[anno_rgb>=5] = 1
anno_rgb += 1
anno_rgb[0,0] = 0
#anno_lbl = anno_rgb[:,:,0] + (anno_rgb[:,:,1] << 8) + (anno_rgb[:,:,2] << 16)
anno_lbl = anno_rgb
# Convert the 32bit integer color to 1, 2, ... labels.
# Note that all-black, i.e. the value 0 for background will stay 0.
#colors, labels = np.unique(anno_lbl, return_inverse=True)
colors = np.unique(anno_lbl)
labels = anno_lbl
# But remove the all-0 black, that won't exist in the MAP!
HAS_UNK = 0 in colors
if HAS_UNK:
    print("Found a full-black pixel in annotation image, assuming it means 'unknown' label, and will thus not be present in the output!")
    print("If 0 is an actual label for you, consider writing your own code, or simply giving your labels only non-zero values.")
    colors = colors[1:]
#else:
#    print("No single full-black pixel found in annotation image. Assuming there's no 'unknown' label!")

# Compute the number of classes in the label image.
# We subtract one because the number shouldn't include the value 0 which stands
# for "unknown" or "unsure".
n_labels = len(set(labels.flat)) - int(HAS_UNK)
print(n_labels, " labels", (" plus \"unknown\" 0: " if HAS_UNK else ""), set(labels.flat))

###########################
### Setup the CRF model ###
###########################
use_2d = False
#use_2d = True
if use_2d:
    print("Using 2D specialized functions")

    # Example using the DenseCRF2D code
    d = dcrf.DenseCRF2D(img.shape[1], img.shape[0], n_labels)

    # get unary potentials (neg log probability)
    U = unary_from_labels(labels, n_labels, gt_prob=0.7, zero_unsure=HAS_UNK)
    d.setUnaryEnergy(U)

    ## This adds the color-independent term, features are the locations only.
    #d.addPairwiseGaussian(sxy=(3, 3), compat=3, kernel=dcrf.DIAG_KERNEL,
                          #normalization=dcrf.NORMALIZE_SYMMETRIC)

    ## This adds the color-dependent term, i.e. features are (x,y,r,g,b).
    #d.addPairwiseBilateral(sxy=(80, 80), srgb=(13, 13, 13), rgbim=img,
                           #compat=10,
                           #kernel=dcrf.DIAG_KERNEL,
                           #normalization=dcrf.NORMALIZE_SYMMETRIC)

    # This adds the color-independent term, features are the locations only.
    d.addPairwiseGaussian(sxy=(10, 10), compat=3, kernel=dcrf.DIAG_KERNEL,
                          normalization=dcrf.NORMALIZE_SYMMETRIC)

    # This adds the color-dependent term, i.e. features are (x,y,r,g,b).
    d.addPairwiseBilateral(sxy=(50, 50), srgb=(20, 20, 20), rgbim=img,
                           compat=10,
                           kernel=dcrf.DIAG_KERNEL,
                           normalization=dcrf.NORMALIZE_SYMMETRIC)
else:
    print("Using generic 2D functions")

    # Example using the DenseCRF class and the util functions
    d = dcrf.DenseCRF(img.shape[1] * img.shape[0], n_labels)

    # get unary potentials (neg log probability)
    U = unary_from_labels(labels, n_labels, gt_prob=0.7, zero_unsure=HAS_UNK)
    d.setUnaryEnergy(U)

    # This creates the color-independent features and then add them to the CRF
    feats = create_pairwise_gaussian(sdims=(3, 3), shape=img.shape[:2])
    d.addPairwiseEnergy(feats, compat=3,
                        kernel=dcrf.DIAG_KERNEL,
                        normalization=dcrf.NORMALIZE_SYMMETRIC)

    # This creates the color-dependent features and then add them to the CRF
    feats = create_pairwise_bilateral(sdims=(80, 80), schan=(13, 13, 13),
                                      img=img, chdim=2)
    d.addPairwiseEnergy(feats, compat=10,
                        kernel=dcrf.DIAG_KERNEL,
                        normalization=dcrf.NORMALIZE_SYMMETRIC)


####################################
### Do inference and compute MAP ###
####################################

# Run five inference steps.
Q = d.inference(5)

# Find out the most probable class for each pixel.
MAP = np.argmax(Q, axis=0)

# Convert the MAP (labels) back to the corresponding colors and save the image.
# Note that there is no "unknown" here anymore, no matter what we had at first.
ipdb.set_trace()
imwrite(fn_output, MAP.reshape(img.shape[0], img.shape[1]))

# Just randomly manually run inference iterations
Q, tmp1, tmp2 = d.startInference()
for i in range(5):
    print("KL-divergence at {}: {}".format(i, d.klDivergence(Q)))
    d.stepInference(Q, tmp1, tmp2)
