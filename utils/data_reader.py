import pickle
from typing import Set, List, Dict

import nltk
import pandas
from pandas import DataFrame
from sklearn.model_selection import train_test_split

from utils.log_hepler import logger
from utils.path_helper import ROOT_DIR
from utils.word2vec_hepler import review2wid, PAD_WORD


def get_all_data(path="data/reviews.json") -> DataFrame:
    return pandas.read_json(ROOT_DIR.joinpath(path), lines=True)


def get_train_dev_test_data(path="data/reviews.json") -> (DataFrame, DataFrame, DataFrame):
    all_data = get_all_data(path)
    train, test = train_test_split(all_data, test_size=0.2, random_state=42)
    train, dev = train_test_split(train, test_size=0.1, random_state=42)
    return train, dev, test


def get_stop_words(path="data/stopwords.txt") -> Set[str]:
    with open(ROOT_DIR.joinpath(path)) as f:
        return set(f.read().splitlines())


def get_punctuations(path="data/punctuations.txt") -> Set[str]:
    with open(ROOT_DIR.joinpath(path)) as f:
        return set(f.read().splitlines())


def get_max_review_length(data: DataFrame, percentile: float = 0.85) -> int:
    """
    We set the max review length to 85% percentile of all data.
    """
    review_lengths = data["review"] \
        .groupby(data["userID"]) \
        .apply(lambda words: len(" ".join(words).split()))
    max_length_user = int(review_lengths.quantile(percentile, interpolation="lower"))

    review_lengths = data["review"] \
        .groupby(data["itemID"]) \
        .apply(lambda words: len(" ".join(words).split()))
    max_length_item = int(review_lengths.quantile(percentile, interpolation="lower"))

    return max(max_length_item, max_length_user)


def process_raw_data(in_path="data/Digital_Music_5.json", out_path="data/reviews.json") -> DataFrame:
    logger.info("reading raw data...")
    df = pandas.read_json(ROOT_DIR.joinpath(in_path), lines=True)
    df = df[["reviewerID", "asin", "reviewText", "overall"]]
    df.columns = ["userID", "itemID", "review", "rating"]
    stop_words = get_stop_words()
    punctuations = get_punctuations()
    lemmatizer = nltk.WordNetLemmatizer()

    def clean_review(review: str):
        review = review.lower()
        assert "'" not in punctuations
        for p in punctuations:
            review = review.replace(p, " ")
        tokens = review.split()
        tokens = [word for word in tokens if word not in stop_words]
        tokens = [lemmatizer.lemmatize(word) for word in tokens]
        return " ".join(tokens)

    logger.info("cleaning review text...")
    df["review"] = df["review"].apply(clean_review)
    df.to_json(ROOT_DIR.joinpath(out_path), orient="records", lines=True)
    logger.info("Processed data saved.")


def get_reviews_in_idx(data: DataFrame, max_length) -> (Dict[str, List[int]], Dict[str, List[int]]):
    def pad_review(reviews: List[str]) -> str:
        joint = " ".join(reviews).split(" ")
        if len(joint) >= max_length:
            pad = joint[:max_length]
        else:
            pad = joint + [PAD_WORD] * (max_length - len(joint))
        return " ".join(pad)

    review_by_user = data["review"] \
        .groupby(data["userID"]) \
        .apply(pad_review) \
        .apply(review2wid) \
        .to_dict()

    review_by_item = data["review"] \
        .groupby(data["itemID"]) \
        .apply(pad_review) \
        .apply(review2wid) \
        .to_dict()

    return review_by_user, review_by_item


if __name__ == "__main__":
    process_raw_data()
    train_data, dev_data, test_data = get_train_dev_test_data()
    known_data = pandas.concat([train_data, dev_data])
    max_length = get_max_review_length(known_data)
    user_review, item_review = get_reviews_in_idx(known_data, max_length)
    pickle.dump(user_review, open(ROOT_DIR.joinpath("data/user_review_word_idx.p"), "wb"))
    pickle.dump(item_review, open(ROOT_DIR.joinpath("data/item_review_word_idx.p"), "wb"))
