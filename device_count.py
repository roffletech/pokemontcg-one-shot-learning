import torch

# This should print the number of GPUs available.  
# Please update the line that says "net = nn.DataParallel(net,device_ids=[0])" in train.py accordingly. 
# If there are 2 GPUs available, then the line should be "net = nn.DataParallel(net,device_ids=[0,1,2,3])"

print(torch.cuda.device_count())