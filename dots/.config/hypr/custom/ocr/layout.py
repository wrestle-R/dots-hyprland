"""Plain-text reconstruction from text-box geometry, without rewriting recognized text."""
from dataclasses import dataclass
from statistics import median

@dataclass
class Region:
    left: float
    top: float
    right: float
    bottom: float
    text: str
    @property
    def height(self): return max(1.0,self.bottom-self.top)
    @property
    def center(self): return (self.top+self.bottom)/2


def reconstruct(boxes,texts,edges=None):
    regions=[]
    for index,(box,text) in enumerate(zip(boxes,texts)):
        text=text.strip()
        if not text:continue
        xs=[float(p[0]) for p in box];ys=[float(p[1]) for p in box]
        left,right=edges[index] if edges else (min(xs),max(xs))
        regions.append(Region(left,min(ys),right,max(ys),text))
    if not regions:return ''
    # Cluster by vertical overlap, with a center-distance guard for adjacent lines.
    rows=[]
    for item in sorted(regions,key=lambda r:(r.center,r.left)):
        candidates=[]
        for row in rows[-4:]:
            overlap=min(item.bottom,max(r.bottom for r in row))-max(item.top,min(r.top for r in row))
            distance=abs(item.center-median(r.center for r in row))
            if overlap>=0.40*min(item.height,median(r.height for r in row)) and distance<0.65*max(item.height,median(r.height for r in row)):
                candidates.append((distance,row))
        if candidates:min(candidates,key=lambda v:v[0])[1].append(item)
        else:rows.append([item])
    rows.sort(key=lambda row:median(r.center for r in row))
    for row in rows:row.sort(key=lambda r:r.left)
    anchor=min(row[0].left for row in rows)
    pitches=[(r.right-r.left)/len(r.text) for r in regions if len(r.text)>=15 and r.right>r.left]
    if not pitches:pitches=[(r.right-r.left)/len(r.text) for r in regions if len(r.text)>=5 and r.right>r.left]
    pitch=median(pitches) if pitches else median(r.height for r in regions)*0.55
    pitch=max(2.0,pitch)
    centers=[median(r.center for r in row) for row in rows]
    gaps=sorted(b-a for a,b in zip(centers,centers[1:]) if b>a)
    normal_gap=median(gaps[:max(1,(len(gaps)+1)//2)]) if gaps else 1
    result=[]
    for i,row in enumerate(rows):
        if i:
            blank=min(3,max(0,round((centers[i]-centers[i-1])/max(1,normal_gap))-1))
            result.extend(['']*blank)
        indent=min(120,max(0,round((row[0].left-anchor)/pitch)))
        line=' '*indent+row[0].text
        for left,right in zip(row,row[1:]):
            spaces=min(120,max(1,round((right.left-left.right)/pitch)))
            line+=' '*spaces+right.text
        result.append(line.rstrip())
    return '\n'.join(result)+'\n'
