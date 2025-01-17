# -*- coding: utf-8 -*-

import torchvision
import torchvision.datasets as dset
import torchvision.transforms as transforms
from torch.utils.data import DataLoader,Dataset
import matplotlib.pyplot as plt
import torchvision.utils
import numpy as np
import random
from PIL import Image
import torch
from torch.autograd import Variable
import PIL.ImageOps    
import torch.nn as nn
from torch import optim
import torch.nn.functional as F
import cv2
from matplotlib import pyplot as plt
import os
#from torchsummary import summary
import imgaug.augmenters as iaa

from time import time
import random
import torchvision.models as models
import pickle


"""## Helper functions
Set of helper functions
"""

def imshow(img,text=None,should_save=False):
    npimg = img.numpy()
    plt.axis("off")
    if text:
        plt.text(75, 8, text, style='italic',fontweight='bold',
            bbox={'facecolor':'white', 'alpha':0.8, 'pad':10})
    plt.imshow(np.transpose(npimg, (1, 2, 0)))
    plt.show()    

def show_plot(iteration,loss):
    plt.plot(iteration,loss)
    plt.show()

"""## Configuration Class
A simple class to manage configuration
"""

class Config():
    training_dir = "..\pokemon-image-dl-app\cardDatabaseFull\\"
    testing_dir = "..\pokemon-image-dl-app\cardDatabaseFull\\"

    train_batch_size = 48

    train_number_epochs = 300

"""## Custom Dataset Class
This dataset generates a pair of images. 0 for geniune pair and 1 for imposter pair
"""

class SiameseNetworkDataset(Dataset):
    
    def __init__(self,imageFolderDataset,transform=None,should_invert=True):
        self.imageFolderDataset = imageFolderDataset    
        self.transform = transform
        self.should_invert = should_invert

    def __getitem__(self,index):
        try:
            # Get an image
            img0_tuple = random.choice(self.imageFolderDataset.imgs)

            # Get an image from the same class
            while True:
                #keep looping till the same class image is found
                img1_tuple = random.choice(self.imageFolderDataset.imgs) 
                if img0_tuple[1]==img1_tuple[1]:
                    break

            # Get an image from a different class
            while True:
                #keep looping till a different class image is found
                    
                img2_tuple = random.choice(self.imageFolderDataset.imgs) 
                if img0_tuple[1] !=img2_tuple[1]:
                    break

            #width,height = (100,150)
            width,height = (244,244)

            pathList = []
            pathList.append((img0_tuple[0],img1_tuple[0],img2_tuple[0]))

            img0 = Image.open(img0_tuple[0]).resize((width,height))
            img1 = Image.open(img1_tuple[0]).resize((width,height))
            img2 = Image.open(img2_tuple[0]).resize((width,height))
            
            
            # Crop the card art
            img0 = img0.crop((int(0.2*width), int(0.2*height), int(0.8*width), int(0.7*height))) 
            img1 = img1.crop((int(0.2*width), int(0.2*height), int(0.8*width), int(0.7*height))) 
            img2 = img2.crop((int(0.2*width), int(0.2*height), int(0.8*width), int(0.7*height))) 
            
            
            img0 = img0.convert("RGBA")
            img1 = img1.convert("RGBA")
            img2 = img2.convert("RGBA")
            
            if self.should_invert:
                img0 = PIL.ImageOps.invert(img0)
                img1 = PIL.ImageOps.invert(img1)
                img2 = PIL.ImageOps.invert(img2)

            if self.transform is not None:
                img0 = self.transform(img0)
                img1 = self.transform(img1)
                img2 = self.transform(img2)
            
            # anchor, positive image, negative image
            return img0, img1 , img2, pathList
        except IOError:
            print(f'Error loading image {img0_tuple[0]}, skipping.')
            return None

    def __len__(self):
        return len(self.imageFolderDataset.imgs)

"""## Using Image Folder Dataset"""

if __name__ == '__main__':

    folder_dataset = dset.ImageFolder(root=Config.training_dir)

    # Commented out IPython magic to ensure Python compatibility.
    class ImgAugTransform:
        def __init__(self):
            self.aug = iaa.Sequential([
                #iaa.Scale((224, 224)),
                iaa.Sometimes(0.25, iaa.GaussianBlur(sigma=(0, 3.0))),
                #iaa.Affine(rotate=(-20, 20), mode='symmetric'),
                iaa.Sometimes(0.25,
                        iaa.OneOf([iaa.Dropout(p=(0, 0.1)),
                                    iaa.CoarseDropout(0.1, size_percent=0.5)])),
                iaa.AddToHueAndSaturation(value=(-10, 10), per_channel=True)
            ])

        def __call__(self, img):
            img = np.array(img)
            return self.aug.augment_image(img)

    # https://colab.research.google.com/drive/109vu3F1LTzD1gdVV6cho9fKGx7lzbFll#scrollTo=aUpukiy8sBKx
    siamese_dataset = SiameseNetworkDataset(imageFolderDataset=folder_dataset,
                                            transform=transforms.Compose([
                                                        transforms.Grayscale(num_output_channels=3),
                                                        #transforms.Resize((100,100)),
                                                        transforms.Resize((244,244)),
                                                        transforms.ColorJitter(brightness=(0.5,1.5),contrast=(0.3,2.0),hue=.05, saturation=(.0,.15)),
                                                        #transforms.RandomHorizontalFlip(),
                                                        #transforms.RandomRotation(10),
                                                        
                                                        transforms.RandomAffine(0, translate=(0,0.3), scale=(0.6,1.8), shear=(0.0,0.4)),
                                                        transforms.ToTensor(),
                                                        transforms.Normalize([0.485, 0.456, 0.406],
                                                                                                                                                                [0.229, 0.224, 0.225]),
                                                    ])
                                        ,should_invert=False)



    vis_dataloader = DataLoader(siamese_dataset,
                            shuffle=True,
                            num_workers=8,    #change to 2?
                            #num_workers=0,
                            batch_size=8)
    dataiter = iter(vis_dataloader)
        
    class SiameseNetwork(nn.Module):
        def __init__(self):
            super(SiameseNetwork, self).__init__()


            #self.resnet = models.resnet152(pretrained=True)
            self.resnet = models.resnet101(pretrained=True)
            #self.resnet = models.resnet50(pretrained=True)

            #self.resnet = torch.nn.Sequential(*(list(self.resnet.children())[:-1]))

        def forward_once(self, x):
            '''
            output = self.cnn1(x)
            output = output.view(output.size()[0], -1)
            output = self.fc1(output)
            #print(output.shape)
            #print(output)
            '''
            #begin = time()
            output = self.resnet(x)
            #print('Time for forward prop: ', time()-begin)

            return output
            

        def forward(self, input1, input2, input3):
            output1 = self.forward_once(input1)
            output2 = self.forward_once(input2)
            output3 = self.forward_once(input3)

            return output1, output2, output3

    """## Contrastive Loss / Triplet Loss"""

    class ContrastiveLoss(torch.nn.Module):
        """
        Contrastive loss function.
        Based on: http://yann.lecun.com/exdb/publis/pdf/hadsell-chopra-lecun-06.pdf
        """

        def __init__(self, margin=2.0):
            super(ContrastiveLoss, self).__init__()
            self.margin = margin

        def forward(self, output1, output2, label):
            #begin = time()
            euclidean_distance = F.pairwise_distance(output1, output2, keepdim = True)
            loss_contrastive = torch.mean((1-label) * torch.pow(euclidean_distance, 2) +
                                        (label) * torch.pow(torch.clamp(self.margin - euclidean_distance, min=0.0), 2))

            #print('Time for contrastive Loss: ', time()-begin)
            return loss_contrastive


    class TripletLoss(nn.Module):
        """
        Triplet loss
        Takes embeddings of an anchor sample, a positive sample and a negative sample
        """

        def __init__(self, margin):
            super(TripletLoss, self).__init__()
            self.margin = margin

        def forward(self, anchor, positive, negative, size_average=True):
            #begin = time()
            distance_positive = (anchor - positive).pow(2).sum(1)  # .pow(.5)
            distance_negative = (anchor - negative).pow(2).sum(1)  # .pow(.5)
            losses = F.relu(distance_positive - distance_negative + self.margin)

            #print('Time for triplet loss: ', time()-begin)

            return losses.mean() if size_average else losses.sum()

    """## Training Time!"""
    print('Loading train dataloader. . .')
    train_dataloader = DataLoader(siamese_dataset,
                            shuffle=True,
                            num_workers=8,
                            batch_size=Config.train_batch_size)


    net = SiameseNetwork().cuda()

    # Check if we can use multiple GPUs. If so, parallelize the model.
    net = nn.DataParallel(net,device_ids=[0])
    print('Model parallelized')
    '''
    print('Loading model. . .')
    loadPath = './res-resnet101-e245-b24.pth'
    '''
    #loadPath = './res-resnet101-e48-b24.pth'
    '''
    net.load_state_dict(torch.load(loadPath))
    print('\n\n\n\n\n Loaded model')
    '''
    #net = SiameseNetwork(Bottleneck, [3,4,23,3])
    #criterion = ContrastiveLoss()
    margin = 2.
    criterion = TripletLoss(margin)

    optimizer = optim.Adam(net.parameters(),lr = 0.0005 )

    counter = []
    loss_history = [] 
    iteration_number= 0

    # If we are loading a checkpoint
    checkpoint_epoch = 0 # change this to the epoch you want to load.  Must have a checkpoint file for that epoch
    #loadPath = f"./checkpoint_{checkpoint_epoch}.pth"
    '''
    net.load_state_dict(torch.load(loadPath))
    print('\n\n\n\n\n Loaded model')
    '''

    prevNum = -1
    print_interval = 1
    for epoch in range(checkpoint_epoch,Config.train_number_epochs):
        print(f'Starting epoch {epoch}')
        begin = time()
        for i, data in enumerate(train_dataloader,0):
            if data is None:
                print("Skipping batch")
                continue
            img_anc, img_pos, img_neg,_ = data
            img_anc, img_pos, img_neg = img_anc.cuda(), img_pos.cuda(), img_neg.cuda()
            optimizer.zero_grad()
            output1,output2,output3 = net(img_anc, img_pos , img_neg)
            loss_contrastive = criterion(output1,output2,output3)
            loss_contrastive.backward()
            optimizer.step()
            # Print the loss at regular intervals
            if i % print_interval == 0:
                print(f'Epoch {epoch}, Iteration {i}, Loss = {loss_contrastive.item()}, time = {time()-begin}')
            # To prevent repetition of epoch
            if i %10 == 0 and prevNum != epoch:
                print("Epoch number {}\n Current loss {}\n".format(epoch,loss_contrastive.item()))
                iteration_number +=10
                counter.append(iteration_number)
                loss_history.append(loss_contrastive.item())
                prevNum = epoch

        # Save the model after each epoch
        saveCheckpoint = f"checkpoint_{epoch}.pth"
        # Check if directory exists and create it if it doesn't
        if not os.path.exists(os.path.dirname(saveCheckpoint)):
            os.makedirs(os.path.dirname(saveCheckpoint))

        torch.save(net.state_dict(), saveCheckpoint)
        print(time()-begin, 's has passed')

    savePath = './res.pth'
    torch.save(net.state_dict(), savePath)

    #savePath = './resL-300-withRotate.pth'
    savePath = './res-300-normalized.pth'
    torch.save(net.state_dict(), savePath)

