from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd
from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

# In-memory user store for demo purposes only.
USERS: Dict[str, str] = {}


@dataclass
class Recommendation:
    name: str
    price: float
    rating: float
    insight: str
    explanation: str
    score: float


class ProductRecommender:
    """Handles product loading, cleaning, and recommendation scoring."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.df = self._load_and_clean_data()

    def _load_and_clean_data(self) -> pd.DataFrame:
        df = pd.read_csv(self.file_path)
        df.columns = (
            df.columns.str.strip().str.lower().str.replace(" ", "_", regex=False)
        )

        required_columns = [
            "name",
            "category",
            "price",
            "rating",
            "review_count",
            "performance_score",
            "battery_score",
            "camera_score",
            "value_score",
            "usage_tags",
            "review_highlight",
        ]

        for column in required_columns:
            if column not in df.columns:
                df[column] = None

        numeric_columns = [
            "price",
            "rating",
            "review_count",
            "performance_score",
            "battery_score",
            "camera_score",
            "value_score",
        ]

        for column in numeric_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        df["name"] = df["name"].fillna("Unnamed Product")
        df["category"] = df["category"].fillna("Other")
        df["rating"] = df["rating"].fillna(df["rating"].median())
        df["price"] = df["price"].fillna(df["price"].median())
        df["review_count"] = df["review_count"].fillna(0)
        df["review_highlight"] = df["review_highlight"].fillna(
            "Customers appreciate the overall quality."
        )
        df["usage_tags"] = df["usage_tags"].fillna("daily")

        for score_col in [
            "performance_score",
            "battery_score",
            "camera_score",
            "value_score",
        ]:
            df[score_col] = df[score_col].fillna(df["rating"])

        return df

    def get_categories(self) -> List[str]:
        return sorted(self.df["category"].dropna().unique().tolist())

    def recommend(
        self,
        category: str,
        min_budget: float,
        max_budget: float,
        priority: str,
        usage: str,
        top_n: int = 3,
    ) -> List[Recommendation]:
        filtered = self.df[
            (self.df["category"].str.lower() == category.lower())
            & (self.df["price"] >= min_budget)
            & (self.df["price"] <= max_budget)
        ].copy()

        if filtered.empty:
            return []

        priority_map = {
            "performance": "performance_score",
            "battery": "battery_score",
            "camera": "camera_score",
            "value": "value_score",
        }
        priority_col = priority_map.get(priority.lower(), "value_score")

        # Scoring model: weighted rating + priority score + usage boost + review confidence.
        filtered["usage_match"] = filtered["usage_tags"].str.lower().str.contains(
            usage.lower()
        )
        filtered["usage_boost"] = filtered["usage_match"].apply(lambda match: 0.4 if match else 0.0)

        filtered["review_confidence"] = (filtered["review_count"] / 1000).clip(0, 0.5)

        filtered["final_score"] = (
            filtered["rating"] * 0.55
            + filtered[priority_col] * 0.30
            + filtered["usage_boost"]
            + filtered["review_confidence"]
        )

        top = filtered.sort_values("final_score", ascending=False).head(top_n)

        recommendations: List[Recommendation] = []
        for _, row in top.iterrows():
            explanation_parts = ["Highly rated by users"]

            if row["usage_match"]:
                explanation_parts.append(f"Strong fit for {usage.title()} usage")

            if priority.lower() == "performance":
                explanation_parts.append("Best for gaming and heavy workloads")
            elif priority.lower() == "battery":
                explanation_parts.append("Great battery life for extended sessions")
            elif priority.lower() == "camera":
                explanation_parts.append("Excellent camera experience for creators")
            else:
                explanation_parts.append("Outstanding overall value for money")

            recommendations.append(
                Recommendation(
                    name=str(row["name"]),
                    price=float(row["price"]),
                    rating=float(row["rating"]),
                    insight=str(row["review_highlight"]),
                    explanation=" • ".join(explanation_parts),
                    score=float(row["final_score"]),
                )
            )

        return recommendations


recommender = ProductRecommender("data/products.csv")


def login_required(view_func):
    def wrapper(*args, **kwargs):
        if "user" not in session:
            flash("Please login to access that page.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    wrapper.__name__ = view_func.__name__
    return wrapper


@app.route("/")
def home():
    return render_template("home.html", user=session.get("user"))


@app.route("/retail")
@login_required
def retail():
    categories = recommender.get_categories()
    return render_template("retail.html", categories=categories, user=session.get("user"))


@app.route("/recommend", methods=["POST"])
@login_required
def recommend():
    category = request.form.get("category", "")
    min_budget = float(request.form.get("min_budget", 0))
    max_budget = float(request.form.get("max_budget", 999999))
    priority = request.form.get("priority", "value")
    usage = request.form.get("usage", "daily")

    recommendations = recommender.recommend(
        category=category,
        min_budget=min_budget,
        max_budget=max_budget,
        priority=priority,
        usage=usage,
    )

    return render_template(
        "results.html",
        recommendations=recommendations,
        selected={
            "category": category,
            "min_budget": min_budget,
            "max_budget": max_budget,
            "priority": priority,
            "usage": usage,
        },
        user=session.get("user"),
    )


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("signup"))

        if username in USERS:
            flash("User already exists. Please login.", "warning")
            return redirect(url_for("login"))

        USERS[username] = password
        flash("Signup successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html", user=session.get("user"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        if USERS.get(username) == password:
            session["user"] = username
            flash("Login successful.", "success")
            return redirect(url_for("home"))

        flash("Invalid credentials.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html", user=session.get("user"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
