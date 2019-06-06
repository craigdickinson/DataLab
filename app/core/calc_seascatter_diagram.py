import pandas as pd


def calc_seascatter_diagram(df, hs_bins, tp_bins):
    """Create seascatter diagram data frame."""

    # df = pd.DataFrame(np.vstack((hs, tp)).T, columns=['Hs', 'Tp'])
    df.columns = ["Hs", "Tp"]

    # Drop events that are nan
    df_nan = df[df["Hs"].isnull() & df["Tp"].isnull()]
    df = df.drop(df_nan.index)

    a = pd.cut(df["Hs"], hs_bins)
    b = pd.cut(df["Tp"], tp_bins)

    # Need to convert bins to object type to prevent type error with crosstab
    a = a.astype("object")
    b = b.astype("object")

    scatter = pd.crosstab(index=a, columns=b, normalize=True) * 100
    scatter = scatter.apply(pd.to_numeric)

    # Need to convert index and column axes from categorical to object type to allow summation
    scatter.index = scatter.index.astype("object")
    scatter.columns = scatter.columns.astype("object")
    scatter["All"] = scatter.sum(axis=1)
    scatter.loc["All"] = scatter.sum()

    return scatter
