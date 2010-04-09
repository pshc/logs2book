all: fools.log.pdf

%.log.pdf: %.log.tex
	pdflatex $<

fools.log.tex: convert.py
	./convert.py fools.log

clean:
	rm *.aux *.log.log
