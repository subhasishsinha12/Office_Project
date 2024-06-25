from setuptools import find_packages, setup
from typing import List

hypen_e_dot ='-e .'
def get_requirements(file_path:str) ->List[str]:
    '''
    Function will return the list of requirements 

    '''
    requirement=[]
    with open(file_path) as file_obj:
        requirement= file_obj.readlines()
        requirement= [req.replace("\n","") for req in requirement]

        if hypen_e_dot in requirement:
            requirement.remove(hypen_e_dot)
    return(requirement)

setup (
name='Office_Project_1',
version='0.0.1',
author='Subhasish Sinha',
author_email='subhasishsinha12@gmail.com',
packages=find_packages(),
install_requires=get_requirements('requirement.txt')
)