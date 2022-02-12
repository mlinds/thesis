#%%
import pandas as pd
import numpy as np

df = pd.DataFrame(np.arange(1,101).reshape(10,10))
df
df.style.to_latex('../document/tables/testtable.tex',)
df.plot(table=True).get_figure().savefig('../document/figures/testfig.png',Label="Test Table 1")
# %%
