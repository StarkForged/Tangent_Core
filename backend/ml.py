"""Small NumPy-only versions of the scikit-learn pieces the analyzer uses.

They follow scikit-learn's algorithms (StandardScaler, DBSCAN, IsolationForest)
so the app does not need scikit-learn + SciPy, which are too large for the
Vercel function bundle.
"""
import math
import numpy as np

EULER_GAMMA = 0.5772156649015329


class StandardScaler:
    def fit_transform(self, X):
        X = np.asarray(X, dtype=float)
        self.mean_ = X.mean(axis=0)
        scale = X.std(axis=0)
        self.scale_ = np.where(scale == 0, 1.0, scale)
        return (X - self.mean_) / self.scale_


class DBSCAN:
    def __init__(self, eps=0.5, min_samples=5, n_jobs=None):
        self.eps, self.min_samples = eps, min_samples

    def fit_predict(self, X):
        X = np.asarray(X, dtype=float)
        n = len(X)
        dist = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2))
        neighbors = [np.flatnonzero(row <= self.eps) for row in dist]
        core = np.array([len(nb) >= self.min_samples for nb in neighbors])
        labels = np.full(n, -1, dtype=int)
        label = 0
        for i in range(n):
            if labels[i] != -1 or not core[i]:
                continue
            labels[i] = label
            stack = [i]
            while stack:
                point = stack.pop()
                if not core[point]:
                    continue  # Border points join the cluster but do not expand it.
                for nb in neighbors[point]:
                    if labels[nb] == -1:
                        labels[nb] = label
                        stack.append(nb)
            label += 1
        return labels


def _average_path_length(n):
    n = np.asarray(n, dtype=float)
    out = np.zeros_like(n)
    out[n == 2] = 1.0
    big = n > 2
    out[big] = 2.0 * (np.log(n[big] - 1.0) + EULER_GAMMA) - 2.0 * (n[big] - 1.0) / n[big]
    return out


class IsolationForest:
    def __init__(self, n_estimators=100, contamination=0.1, random_state=None, n_jobs=None):
        self.n_estimators, self.contamination, self.random_state = n_estimators, contamination, random_state

    def _build(self, X, rng, depth, max_depth):
        n = len(X)
        if depth >= max_depth or n <= 1:
            return ('leaf', n)
        varying = np.flatnonzero(X.max(axis=0) > X.min(axis=0))
        if not len(varying):
            return ('leaf', n)
        feature = int(rng.choice(varying))
        low, high = X[:, feature].min(), X[:, feature].max()
        threshold = rng.uniform(low, high)
        left = X[:, feature] <= threshold
        return ('split', feature, threshold,
                self._build(X[left], rng, depth + 1, max_depth),
                self._build(X[~left], rng, depth + 1, max_depth))

    def _path_lengths(self, tree, X, depth=0):
        if tree[0] == 'leaf':
            return np.full(len(X), depth + _average_path_length([tree[1]])[0])
        _, feature, threshold, left_tree, right_tree = tree
        out = np.empty(len(X))
        left = X[:, feature] <= threshold
        if left.any():
            out[left] = self._path_lengths(left_tree, X[left], depth + 1)
        if (~left).any():
            out[~left] = self._path_lengths(right_tree, X[~left], depth + 1)
        return out

    def fit(self, X):
        X = np.asarray(X, dtype=float)
        rng = np.random.default_rng(self.random_state)
        self.max_samples_ = min(256, len(X))
        max_depth = int(math.ceil(math.log2(max(self.max_samples_, 2))))
        self.trees_ = []
        for _ in range(self.n_estimators):
            sample = X[rng.choice(len(X), self.max_samples_, replace=False)]
            self.trees_.append(self._build(sample, rng, 0, max_depth))
        self.offset_ = np.percentile(self.score_samples(X), 100.0 * self.contamination)
        return self

    def score_samples(self, X):
        X = np.asarray(X, dtype=float)
        depths = np.mean([self._path_lengths(tree, X) for tree in self.trees_], axis=0)
        return -(2.0 ** (-depths / _average_path_length([self.max_samples_])[0]))

    def decision_function(self, X):
        return self.score_samples(X) - self.offset_

    def fit_predict(self, X):
        return np.where(self.fit(X).decision_function(X) < 0, -1, 1)
