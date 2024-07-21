import pandas


df_hcp = pandas.read_csv("hcp.csv")
df_scraped = pandas.read_csv("linkedin_scraped.csv")

df_hcp.merge(df_scraped, on="profile_url", how="left").to_csv("merged.csv")
