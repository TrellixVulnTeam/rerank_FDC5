"""PyTorch dataset classes for the image captioning training and testing datasets"""

import os
import h5py
import json
import torch
from torch.utils.data import Dataset
from torchvision.transforms import transforms
import faiss

from scipy.misc import imresize

from toolkit.utils import (
    DATA_CAPTIONS,
    DATA_CAPTION_LENGTHS,
    TRAIN_SPLIT,
    VALID_SPLIT,
    TEST_SPLIT,
    ENCODED_METAS_FILENAME,
    DATASET_SPLITS_FILENAME,
    IMAGENET_IMAGES_MEAN,
    IMAGENET_IMAGES_STD,
    CAPTIONS_FILENAME
)


class CaptionDataset(Dataset):
    """
    PyTorch Dataset that provides batches of images of a given split
    """

    def __init__(self, dataset_splits_dir, features_fn, normalize=None, features_scale_factor=1):
        """
        :param data_dir: folder where data files are stored
        :param features_fn: Filename of the image features file
        :param split: split, indices of images that should be included
        :param normalize: PyTorch normalization transformation
        :param features_scale_factor: Additional scale factor, applied before normalization
        """
        self.image_features = h5py.File(features_fn, "r")
        self.features_scale_factor = features_scale_factor

        # Set PyTorch transformation pipeline
        self.transform = normalize

        # Load image meta data, including captions
        with open(os.path.join(dataset_splits_dir, ENCODED_METAS_FILENAME)) as f:
            self.image_metas = json.load(f)

        #load captions with text for retrieval
        with open(os.path.join(dataset_splits_dir, CAPTIONS_FILENAME)) as f:
            self.captions_text = json.load(f)

        self.captions_per_image = len(next(iter(self.image_metas.values()))[DATA_CAPTIONS])

        with open(os.path.join(dataset_splits_dir, DATASET_SPLITS_FILENAME)) as f:
            self.split = json.load(f)

    def get_image_features(self, coco_id):
        image_data = self.image_features[coco_id][()]
        # scale the features with given factor
        image_data = image_data * self.features_scale_factor
        image = torch.FloatTensor(image_data)
        if self.transform:
            image = self.transform(image)
        return image


    # def get_image_features(self, coco_id):
    #     return torch.zeros((2, 7,7,2048))

    def __getitem__(self, i):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError


class CaptionTrainDataset(CaptionDataset):
    """
    PyTorch training dataset that provides batches of images with a corresponding caption each.
    """

    def __init__(self, dataset_splits_dir, features_fn, normalize=None, features_scale_factor=1):
        super().__init__(dataset_splits_dir, features_fn,
                         normalize, features_scale_factor)
        self.split = self.split[TRAIN_SPLIT]

    def __getitem__(self, i):
        # Convert index depending on the dataset split
        coco_id = self.split[i // self.captions_per_image]
        caption_index = i % self.captions_per_image

        image = self.get_image_features(coco_id)
        caption = torch.LongTensor(self.image_metas[coco_id][DATA_CAPTIONS][caption_index])
        caption_length = torch.LongTensor([self.image_metas[coco_id][DATA_CAPTION_LENGTHS][caption_index]])

        return image, caption, caption_length

    def __len__(self):
        return len(self.split) * self.captions_per_image


class CaptionEvalDataset(CaptionDataset):
    """
    PyTorch test dataset that provides batches of images and all their corresponding captions.

    """

    def __init__(self, dataset_splits_dir, features_fn, normalize=None, features_scale_factor=1, eval_split="val"):
        super().__init__(dataset_splits_dir, features_fn,
                         normalize, features_scale_factor)
        if eval_split == "val":
            self.split = self.split[VALID_SPLIT]
        else:
            self.split = self.split[TEST_SPLIT]

    def __getitem__(self, i):
        # Convert index depending on the dataset split
        coco_id = self.split[i]

        image = self.get_image_features(coco_id)
        all_captions_for_image = torch.LongTensor(self.image_metas[coco_id][DATA_CAPTIONS])
        caption_lengths = torch.LongTensor(self.image_metas[coco_id][DATA_CAPTION_LENGTHS])

        return image, all_captions_for_image, caption_lengths, coco_id

    def __len__(self):
        return len(self.split)





# class CaptionTrainRetrievalDataset(CaptionDataset):
#     """
#     PyTorch training dataset that provides batches of images with a corresponding caption each.
#     """

#     def __init__(self, dataset_splits_dir, features_fn, normalize=None, features_scale_factor=1):
#         super().__init__(dataset_splits_dir, features_fn,
#                          normalize, features_scale_factor)
#         self.split = self.split[TRAIN_SPLIT]
#         #self.model = roberta...

#     def __getitem__(self, i):
#         # Convert index depending on the dataset split
#         coco_id = self.split[i // self.captions_per_image]
#         caption_index = i % self.captions_per_image

#         image = self.get_image_features(coco_id)
#         text_caption = self.captions_text[coco_id][caption_index]
#         for i in text_caption:
#             #iterar pelas captions para teres o contexto...
#             text_enc=self.model.encode(text_caption[:MAX_LEN]) #what is max ln?
#             #save target word (next word) in a file...
            
#             torch.cat(image, text_enc)
#             #add to retrieval...

#         return image, caption

#     def __len__(self):
#         return len(self.split) * self.captions_per_image


# class ImageRetrieval():

#     def __init__(self, dim_examples, encoder, train_dataloader_images, device):
#         #print("self dim exam", dim_examples)
#         self.datastore = faiss.IndexFlatL2(dim_examples) #datastore
#         self.encoder= encoder

#         #data
#         self.device=device
#         self.imgs_indexes_of_dataloader = torch.tensor([]).long().to(device)
#         #print("self.imgs_indexes_of_dataloader type", self.imgs_indexes_of_dataloader)

#         #print("len img dataloader", self.imgs_indexes_of_dataloader.size())
#         self._add_examples(train_dataloader_images)
#         #print("len img dataloader final", self.imgs_indexes_of_dataloader.size())
#         #print("como ficou img dataloader final", self.imgs_indexes_of_dataloader)


#     def _add_examples(self, train_dataloader_images):
#         print("\nadding input examples to datastore (retrieval)")
#         for i, (imgs, imgs_indexes) in enumerate(train_dataloader_images):
#             #add to the datastore
#             imgs=imgs.to(self.device)
#             imgs_indexes = imgs_indexes.long().to(self.device)
#             #print("img index type", imgs_indexes)
#             encoder_output = self.encoder(imgs)

#             encoder_output = encoder_output.view(encoder_output.size()[0], -1, encoder_output.size()[-1])
#             input_img = encoder_output.mean(dim=1)
            
#             self.datastore.add(input_img.cpu().numpy())

#             if i%5==0:
#                 print("i and img index of ImageRetrival",i, imgs_indexes)
#                 print("n of examples", self.datastore.ntotal)
#             self.imgs_indexes_of_dataloader= torch.cat((self.imgs_indexes_of_dataloader,imgs_indexes))


#     def _add_examples(self, train_dataloader):
#         print("\nadding input examples to datastore (retrieval)")
#         for i, (image, caption, caption_length) in enumerate(train_dataloader):
#             #add to the datastore
            
#             #o que fazes com a imagem??
#             imgs=imgs.to(self.device)
#             imgs_indexes = imgs_indexes.long().to(self.device)
#             #print("img index type", imgs_indexes)
#             encoder_output = self.encoder(imgs)

#             encoder_output = encoder_output.view(encoder_output.size()[0], -1, encoder_output.size()[-1])
#             input_img = encoder_output.mean(dim=1)
            
#             self.datastore.add(input_img.cpu().numpy())

#             if i%5==0:
#                 print("i and img index of ImageRetrival",i, imgs_indexes)
#                 print("n of examples", self.datastore.ntotal)
#             self.imgs_indexes_of_dataloader= torch.cat((self.imgs_indexes_of_dataloader,imgs_indexes))



#     def retrieve_nearest_for_train_query(self, query_img, k=2):
#         #print("self query img", query_img)
#         D, I = self.datastore.search(query_img, k)     # actual search
#         #print("all nearest", I)
#         #print("I firt", I[:,0])
#         #print("if you choose the first", self.imgs_indexes_of_dataloader[I[:,0]])
#         nearest_input = self.imgs_indexes_of_dataloader[I[:,1]]
#         #print("the nearest input is actual the second for training", nearest_input)
#         #nearest_input = I[0,1]
#         #print("actual nearest_input", nearest_input)
#         return nearest_input

#     def retrieve_nearest_for_val_or_test_query(self, query_img, k=1):
#         D, I = self.datastore.search(query_img, k)     # actual search
#         nearest_input = self.imgs_indexes_of_dataloader[I[:,0]]
#         #print("all nearest", I)
#         #print("the nearest input", nearest_input)
#         return nearest_input


class CaptionTrainRetrievalDataset(CaptionDataset):

    def __init__(self, dataset_splits_dir, features_fn, normalize=None, features_scale_factor=1):
        super().__init__(dataset_splits_dir, features_fn,
                         normalize, features_scale_factor)
        self.split = self.split[TRAIN_SPLIT]
        #self.split = self.split[VALID_SPLIT]
        #TODO: REMOVE VALID SPLIT JUST FOR CHECKING


    def __getitem__(self, i):
        # Convert index depending on the dataset split
        coco_id = self.split[i]

        image = self.get_image_features(coco_id)
        return image, coco_id

    def __len__(self):
        return len(self.split)


class ImageRetrieval():

    def __init__(self, dim_examples, train_dataloader_images, device):
        #print("self dim exam", dim_examples)
        self.datastore = faiss.IndexFlatL2(dim_examples) #datastore

        #data
        self.device=device
        self.imgs_indexes_of_dataloader = torch.tensor([]).long().to(device)
        #print("self.imgs_indexes_of_dataloader type", self.imgs_indexes_of_dataloader)

        #print("len img dataloader", self.imgs_indexes_of_dataloader.size())
        self._add_examples(train_dataloader_images)
        #print("len img dataloader final", self.imgs_indexes_of_dataloader.size())
        #print("como ficou img dataloader final", self.imgs_indexes_of_dataloader)


    def _add_examples(self, train_dataloader_images):
        print("\nadding input examples to datastore (retrieval)")
        for i, (encoder_output, imgs_indexes) in enumerate(train_dataloader_images):
            #add to the datastore
            encoder_output=encoder_output.to(self.device)
            imgs_indexes = torch.tensor(list(map(int, imgs_indexes))).to(self.device)
            #print("\nimages ind", imgs_indexes)
            #print("img index type", imgs_indexes)
            #print("encoder out", encoder_output.size())
            #encoder_output = encoder_output.view(encoder_output.size()[0], -1, encoder_output.size()[-1])
            #print("encoder out", encoder_output.size())
            input_img = encoder_output.mean(dim=1)
            #print("input image size", input_img.size())
            
            self.datastore.add(input_img.cpu().numpy())
            self.imgs_indexes_of_dataloader= torch.cat((self.imgs_indexes_of_dataloader,imgs_indexes))

            if i%5==0:
                print("i and img index of ImageRetrival",i, imgs_indexes)
                print("n of examples", self.datastore.ntotal)
                print("debug mode")
                break
    
    def retrieve_nearest_for_train_query(self, query_img, k=2):
        #print("self query img", query_img)
        D, I = self.datastore.search(query_img, k)     # actual search
        # print("all nearest", I)
        # print("I firt", I[:,0])
        # print("I second", I[:,1])

        # print("if you choose the first", self.imgs_indexes_of_dataloader[I[:,0]])
        # print("this is the img indexes", self.imgs_indexes_of_dataloader)
        # print("n of img index", len(self.imgs_indexes_of_dataloader))
        # print("n of examples", self.datastore.ntotal)

        nearest_input = self.imgs_indexes_of_dataloader[I[:,1]]
        #print("the nearest input is actual the second for training", nearest_input)
        return nearest_input

    def retrieve_nearest_for_val_or_test_query(self, query_img, k=1):
        D, I = self.datastore.search(query_img, k)     # actual search
        nearest_input = self.imgs_indexes_of_dataloader[I[:,0]]
        # print("all nearest", I)
        # print("the nearest input", nearest_input)
        return nearest_input


class Scale(object):
  """Scale transform with list as size params"""

  def __init__(self, size): # interpolation=Image.BILINEAR):
    self.size = size

  def __call__(self, img):
    return imresize(img.numpy().transpose(1,2,0), (224,224))


def get_data_loader(split, batch_size, dataset_splits_dir, image_features_fn, workers, image_normalize=None):

    if not image_normalize:
        normalize = None
        features_scale_factor = 1
    if image_normalize == "imagenet":
        normalize = transforms.Normalize(mean=IMAGENET_IMAGES_MEAN, std=IMAGENET_IMAGES_STD)
        normalize = transforms.Compose([normalize])
        features_scale_factor = 1/255.0
    if image_normalize == "scaleimagenet":
        normalize = transforms.Normalize(mean=IMAGENET_IMAGES_MEAN, std=IMAGENET_IMAGES_STD)
        normalize = transforms.Compose([Scale([224,224]), transforms.ToTensor(), normalize])
        features_scale_factor = 1

    if split == "train":
        data_loader = torch.utils.data.DataLoader(
            CaptionTrainDataset(dataset_splits_dir, image_features_fn, normalize, features_scale_factor),
            batch_size=batch_size, shuffle=True, num_workers=workers, pin_memory=True
        )
    elif split in {"val", "test"}:
        data_loader = torch.utils.data.DataLoader(
            CaptionEvalDataset(dataset_splits_dir, image_features_fn, normalize, features_scale_factor, split),
            batch_size=batch_size, shuffle=True, num_workers=workers, pin_memory=True
        )
    elif split == "retrieval":
        data_loader = torch.utils.data.DataLoader(
                CaptionTrainRetrievalDataset(dataset_splits_dir, image_features_fn, normalize, features_scale_factor),
                batch_size=batch_size, shuffle=False, num_workers=workers, pin_memory=True
            )

    else:
        raise ValueError("Invalid data_loader split. Options: train, val, test")

    return data_loader


def get_retrieval(retrieval_data_loader, device):

    encoder_output_dim = 2048 #faster r-cnn features

    image_retrieval = ImageRetrieval(encoder_output_dim, retrieval_data_loader,device)
  
    
    # for i, (encoder_output, coco_ids) in enumerate(retrieval_data_loader):
    #     print("this is the first batch of images", encoder_output.size())
    #     print("coco ids", coco_ids)
    #     input_imgs = encoder_output.mean(dim=1)
    #     print("this  input_imgs suze after", input_imgs.size())
    #     nearest=image_retrieval.retrieve_nearest_for_train_query(input_imgs.numpy())
    #     print("this is nearest images", nearest)

    #     nearest = image_retrieval.retrieve_nearest_for_val_or_test_query(input_imgs.numpy())
        
    #     print("retrieve for test query", nearest)

        #print(stop)
    #     encoder_output= encoder_output.view(encoder_output.size()[0], -1, encoder_output.size()[-1])
    #     input_imgs = encoder_output.mean(dim=1)
    #     nearest=retrieval.retrieve_nearest_for_train_query(input_imgs.numpy())
    #     print("this is nearest images", nearest)
    #     #falta imprimir o coco id dos nearest 

    #print("stop remove from dataloader o VAL e coloca TRAIN", stop)


    return image_retrieval