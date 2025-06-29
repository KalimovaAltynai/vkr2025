import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple
import plotly.express as px

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def cluster_abstracts(articles: List[Dict], num_clusters: int) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Кластеризация аннотаций с использованием KMeans и SentenceTransformer.

    :param articles: Список словарей с ключами 'id', 'title', 'abstract'
    :param num_clusters: Число кластеров для KMeans
    :return: DataFrame с результатами и центроиды кластеров
    """
    df = pd.DataFrame(articles)
    embeddings = model.encode(df["abstract"].tolist(), show_progress_bar=False)
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    df['cluster'] = kmeans.fit_predict(embeddings)
    return df, kmeans.cluster_centers_

def reduce_dimensions(embeddings: np.ndarray) -> np.ndarray:
    """
    Снижение размерности до 3D с помощью PCA.

    :param embeddings: Массив эмбеддингов
    :return: Массив размерности (n, 3)
    """
    return PCA(n_components=3).fit_transform(embeddings)

def generate_3d_plot(df: pd.DataFrame, title: str = "Кластеризация аннотаций") -> str:
    """
    Создаёт HTML-график 3D кластеризации.

    :param df: DataFrame с координатами и кластерами
    :param title: Заголовок графика
    :return: HTML строка графика (без полного HTML-документа)
    """
    fig = px.scatter_3d(
        df,
        x='x', y='y', z='z',
        color=df['cluster'].astype(str),
        hover_name=df['title'],
        title=title,
        width=900, height=700
    )
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def find_nearest_cluster(query: str, cluster_centers: Dict[int, np.ndarray]) -> int:
    """
    Определяет ближайший кластер к вектору запроса.

    :param query: Строка запроса
    :param cluster_centers: Словарь cluster_id -> center_vector
    :return: Идентификатор ближайшего кластера
    """
    query_vec = model.encode([query])[0]
    return max(
        cluster_centers.items(),
        key=lambda kv: cosine_similarity([query_vec], [kv[1]])[0][0]
    )[0]
