#%%
import pandas as pd
import numpy as np

df = pd.DataFrame(np.arange(1,101).reshape(5,20))
df
df.style.to_latex('../document/tables/testtable.tex',label="TestTable1",caption='nice')
df.plot(table=True).get_figure().savefig('../document/figures/testfig.png')
# %%
