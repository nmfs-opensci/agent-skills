# Evaluation scenarios: virtual-icechunk

Give the agent one scenario at a time, with no other context. None of these may
write to a production Icechunk repository, dataset, or object store; any
execution must target a local temporary directory or an explicitly scratch
prefix. Scenarios 1–3 are planning exercises.

## 1. NASA Earthdata source, object-storage destination

> We want a virtual Icechunk store for a NASA PACE ocean-colour product. The
> files are NetCDF4 in an Earthdata DAAC. We'll publish the store to our
> Source Cooperative account. Where do we start?

## 2. Public cloud source, Source Cooperative destination

> There's a public NOAA dataset on cloud object storage — anonymous access, no
> credentials needed. Roughly 6,000 daily NetCDF files, one time step each.
> Build us a virtual Icechunk store on Source Cooperative.

## 3. A source we produce ourselves

> We generate the NetCDF files for this dataset. Each monthly file holds 4–5
> time steps, the arrays are unchunked, and the time-chunk sizes vary from month
> to month. Users want point time series. Make a virtual Icechunk store from
> them.

## 4. Audit of an older workflow

> Review this virtual Icechunk repository and tell us what to do about it. Point
> the agent at one of the older reference repositories (for example
> `fish-pace/globcolour-Icechunks`) in read-only fashion.

## 5. A claim about browser access

Ask, at the end of any completed scenario:

> Can people read this store directly from a browser, in JavaScript?

## 6. Slow reads, diagnosed

Ask, after scenario 1 or 2:

> The store works but reading it is slow. What would you check?

Follow up with only one of these, and see whether the agent asked first:

> Opening it takes about 90 seconds. Once it's open, a small map slice is fine.

or

> It opens instantly, but pulling a year of data at one point takes forever.

## 7. Slow reads, predicted

Give the agent a plan rather than a store:

> Here's the plan: 6,000 daily files, one time step each, on a European host.
> One Icechunk repo on Source Cooperative, split into four groups by variable.
> Users are on the US east coast and mostly want point time series. Anything
> you'd change?

## 8. Lesson capture

Ask, after scenario 3 or 4:

> What did that teach us that we should write down?
