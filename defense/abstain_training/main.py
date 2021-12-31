import os.path as osp
from accelerate import Accelerator

from bert_finetuning.config import BertOptimConfig
from bert_finetuning.data_loader import GermanDataLoader
from bert_finetuning.eval import eval_model
from bert_finetuning.model import BERTClassifier
from bert_finetuning.train import train_model
from .data import GermanAdversarialData


def main(fp16=False, cpu=False, BASE_PATH=""):
    epochs = 10
    num_labels = 3

    accelerator = Accelerator(fp16=fp16, cpu=cpu)

    data_path = {
        "train": osp.join(BASE_PATH, "datasets/hasoc_dataset/hasoc_german_train.csv"),
        "dev": osp.join(BASE_PATH, "datasets/hasoc_dataset/hasoc_german_validation.csv"),
        "test": osp.join(BASE_PATH, "datasets/hasoc_dataset/hasoc_german_test.csv"),

        "adv": {
            "train": osp.join(BASE_PATH, "datasets/perturbed_sets/results-hasoc_whitebox_charlevel_attack.csv"),
        },
    }

    model_name = "deepset/gbert-base"
    data_loaders = GermanDataLoader(
        data_path,
        model_name,
        do_cleansing=False,
        max_sequence_length=128,
        batch_size=8,
        dataset_cls=GermanAdversarialData,
    )
    model = BERTClassifier(num_labels=num_labels).get_model()
    model = model.to(accelerator.device)
    optim_config = BertOptimConfig(
        model=model, train_dataloader=data_loaders.train_dataloader, epochs=epochs
    )

    # prepare everything
    (
        model,
        optim_config.optimizer,
        optim_config.scheduler,
        data_loaders.train_dataloader,
        data_loaders.validation_dataloader,
    ) = accelerator.prepare(
        model,
        optim_config.optimizer,
        optim_config.scheduler,
        data_loaders.train_dataloader,
        data_loaders.validation_dataloader,
    )

    ## execute the training routine
    model = train_model(
        model=model,
        optimizer=optim_config.optimizer,
        scheduler=optim_config.scheduler,
        train_dataloader=data_loaders.train_dataloader,
        validation_dataloader=data_loaders.validation_dataloader,
        epochs=epochs,
        device=accelerator.device,
        model_name=model_name,
    )

    ## test model performance on unseen test set
    eval_model(model=model, test_dataloader=data_loaders.test_dataloader, device=accelerator.device)


if __name__ == "__main__":
    main()
