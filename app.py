import streamlit as st
import cv2      
import os,urllib
import numpy as np    
import tensorflow as tf
import time
import pytesseract
import time
import glob
import os


from gtts import gTTS
from googletrans import Translator

from spellchecker import SpellChecker
from pipeline import *
spell = SpellChecker()

def main():

   #st.title("VisualSpeaker")

    #st.image("new.png")


    st.subheader("VisualSpeaker")

    st.markdown("") 

    # Your code goes below
    # Our Dataset
    st.markdown("""
    	#### Input Image
        """)
    
    #Load Quantized model
    east_quantized_1 = tf.lite.Interpreter(model_path="east_float16.tflite")
    east_quantized_1.allocate_tensors()
    # Get input and output tensors.
    input_details_detector = east_quantized_1.get_input_details()
    output_details_detector = east_quantized_1.get_output_details()   
    def final(img):

        spell = SpellChecker()
        #Configuration setting to convert image to string.  
        configuration = ("-l eng --oem 3 --psm 12")

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        #1.Text Detection
        img=cv2.resize(img,(512,512))
        img_1 = img.astype('float32')
        east_quantized_1.set_tensor(input_details_detector[0]['index'],np.expand_dims(img_1,axis=0))
        east_quantized_1.invoke()
        ii=east_quantized_1.get_tensor(output_details_detector[0]['index'])
        score_map=ii[0][:,:,0]
        geo_map=ii[0][:,:,1:]

        for ind in [0,1,2,3,4]:
            geo_map[:,:,ind]*=score_map

        #2.ROI Rotate  
        score_map_thresh=0.5
        box_thresh=0.1 
        nms_thres=0.2
        if len(score_map.shape) == 4:
            score_map = score_map[0, :, :, 0]
            geo_map = geo_map[0, :, :, :]

        # filter the score map
        xy_text = np.argwhere(score_map > score_map_thresh)

        # sort the text boxes via the y axis
        xy_text = xy_text[np.argsort(xy_text[:, 0])]

        # restore
        text_box_restored = restore_rectangle(xy_text[:, ::-1], geo_map[xy_text[:, 0], xy_text[:, 1], :]) # N*4*2
        boxes = np.zeros((text_box_restored.shape[0], 9), dtype=np.float32)
        boxes[:, :8] = text_box_restored.reshape((-1, 8))
        boxes[:, 8] = score_map[xy_text[:, 0], xy_text[:, 1]]
        boxes = nms_locality(boxes.astype(np.float64), nms_thres)


        # here we filter some low score boxes by the average score map, this is different from the orginal paper
        for i, box in enumerate(boxes):
            mask = np.zeros_like(score_map, dtype=np.uint8)
            cv2.fillPoly(mask, box[:8].reshape((-1, 4, 2)).astype(np.int32), 1)
            boxes[i, 8] = cv2.mean(score_map, mask)[0]

            if i==4:
                break
        if len(boxes)>0:
            boxes = boxes[boxes[:, 8] > box_thresh]
        boxes[:,:8:2] = np.clip(boxes[:,:8:2], 0, 512 - 1)
        boxes[:,1:8:2] = np.clip(boxes[:,1:8:2], 0, 512 - 1)  
        res = []
        result = []
        if len(boxes)>0:
            for box in boxes:
                box_ =  box[:8].reshape((4, 2))
                if np.linalg.norm(box_[0] - box_[1]) < 8 or np.linalg.norm(box_[3]-box_[0]) < 8:
                    continue
                result.append(box_)
        res.append(np.array(result, np.float32))   

        box_index = []
        brotateParas = []
        filter_bsharedFeatures = []
        for i in range(len(res)):
            rotateParas = []
            rboxes=res[i]
            txt=[]
            for j, rbox in enumerate(rboxes):
                para = restore_roiRotatePara(rbox)
                if para and min(para[1][2:]) > 8:
                    rotateParas.append(para)
                    box_index.append((i, j))
            pts=[]   
            
            
            #3. Text Recognition (From boxes given by Text Detection+ROI Rotate) 
        txt = [] 
        if len(rotateParas) > 0:
            for num in range(len(rotateParas)):
                text=""
                out=rotateParas[num][0]
                crop=rotateParas[num][1]
                points=np.array([[out[0],out[1]],[out[0]+out[2],out[1]],[out[0]+out[2],out[1]+out[3]],[out[0],out[1]+out[3]]])
                angle=rotateParas[num][2] 
                img1=tf.image.crop_to_bounding_box(img,out[1],out[0],out[3],out[2])
                img2=tf.keras.preprocessing.image.random_rotation(img1,angle)
                img2=tf.image.crop_to_bounding_box(img2,crop[1],crop[0],crop[3],crop[2]).numpy()
                img2=cv2.resize(img2,(128,64))
                img2=cv2.detailEnhance(img2)
                plt.show()
                text = pytesseract.image_to_string(img2, config=configuration).strip()
                strn = spell.correction(text)
                strn = re.sub(r"\n", " ",strn)
                strn = re.sub(r"\t", " ", strn)
                strn = re.sub(r'[?|$|.|!]',r'',strn)
                strn = re.sub(r'[^a-zA-Z0-9 ]',r'',strn)
                txt.append(strn)
        
                pts.append(points)

        for i in range(len(txt)):
            cv2.polylines(img,[pts[i]],isClosed=True,color=(255,255,0),thickness=2)
        # cv2.putText(img,txt[i],(pts[i][0][0],pts[i][0][1]),cv2.FONT_HERSHEY_SIMPLEX,0.8, (0, 0, 255), 3)

        return img,txt

    uploaded_file = st.file_uploader("input data", type=["jpg","png","jpeg"])
    
    if uploaded_file is not None:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        #gt = cv2.imdecode(file_bytes, 1)
        uploaded_file.seek(0)
        file_details = {"FileName":uploaded_file.name,"FileType":uploaded_file.type,"FileSize":uploaded_file.size}
        st.write(file_details)
    

        img = cv2.imdecode(file_bytes, 1)
        
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_= img.copy()
        img=cv2.resize(img,(512,512))
        
        im,txt= final(img)
        img=cv2.resize(img,(400,300))
        im=cv2.resize(im,(400,300))
        st.write('Original Image')
        st.image(img)
        
        st.write('Predicted Image')
        st.image(im, channels="BGR")
        st.write("Predicted Texts:",txt)

     
if __name__ == "__main__":
    main() 

try:
    os.mkdir("temp")
except:
    pass
st.markdown("""
    	#### Input text
        """)
translator = Translator()

text = st.text_area("Enter text")
input_language="en"
output_language="en"
tld="com"
global tts
def text_to_speech(input_language, output_language, text, tld):
    
    translation = translator.translate(text, src=input_language, dest=output_language)
    trans_text = translation.text
    tts=gTTS(trans_text, lang=output_language, tld=tld, slow=False)
    try:
        my_file_name = text[0:20]
    except:
        my_file_name = "audio"
    tts.save(f"temp/{my_file_name}.mp3")
    return my_file_name, trans_text


display_output_text = st.checkbox("Display output text")

if st.button("convert"):
    result, output_text = text_to_speech(input_language, output_language, text, tld)
    audio_file = open(f"temp/{result}.mp3", "rb")
    audio_bytes = audio_file.read()
    st.markdown(f"## Your audio:")
    st.audio(audio_bytes, format="audio/mp3", start_time=0)

    if display_output_text:
        st.markdown(f"## Output text:")
        st.write(f" {output_text}")



def remove_files(n):
    mp3_files = glob.glob("temp/*mp3")
    if len(mp3_files) != 0:
        now = time.time()
        n_days = n * 86400
        for f in mp3_files:
            if os.stat(f).st_mtime < now - n_days:
                os.remove(f)
                print("Deleted ", f)


remove_files(7)
