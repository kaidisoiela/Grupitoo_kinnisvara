!pip install pandas sqlalchemy
import streamlit as st
import seaborn as sns
import duckdb
import sklearn
import pandas as pd
import shap
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import RandomForestRegressor
penguins=sns.load_dataset("penguins")